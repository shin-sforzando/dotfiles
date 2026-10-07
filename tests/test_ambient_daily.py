"""Tests for dot_local/bin/executable_ambient-daily.

Run with /usr/bin/python3 on purpose: launchd runs the script with the
system Python 3.9, so a newer interpreter could hide syntax it lacks.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import importlib.util
import io
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
from collections import Counter
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_loader = SourceFileLoader("ambient_daily", str(ROOT / "dot_local/bin/executable_ambient-daily"))
_spec = importlib.util.spec_from_loader("ambient_daily", _loader)
ad = importlib.util.module_from_spec(_spec)
# dataclasses resolve string annotations through sys.modules, so the module
# must be registered before it runs.
sys.modules["ambient_daily"] = ad
_loader.exec_module(ad)

APPS_MD = """---
date: 2026-10-05
---

## 12:52–12:53 · Claude · Ambient Context

file:
url: file:///Applications/Claude.app/

body line

## 13:04–15:16 · Wavebox · Meet · Flipples 定例

url: https://meet.google.com/abc

## 15:20–15:25 · Ghostty · zsh

## 23:57–00:00 · Vivaldi · night reading
"""


def make_config(root: Path) -> ad.Config:
    return ad.Config(
        ac_root=root / "ac",
        vault=root / "vault",
        socket=root / "control.sock",
        prompt_file=root / "prompt.md",
        claude="/nonexistent/claude",
        kb_wait=1.0,
        poll=0.01,
        lock_file=root / "lock",
        notify=False,
    )


class TimelineTest(unittest.TestCase):
    def setUp(self):
        self.blocks = ad.parse_timeline(APPS_MD)

    def test_parses_headings_apps_titles_and_refs(self):
        self.assertEqual(len(self.blocks), 4)
        first = self.blocks[0]
        self.assertEqual((first.start, first.end, first.app, first.title), (772, 773, "Claude", "Ambient Context"))
        self.assertEqual(first.ref, "file:///Applications/Claude.app/")

    def test_title_keeps_inner_separators(self):
        self.assertEqual(self.blocks[1].app, "Wavebox")
        self.assertEqual(self.blocks[1].title, "Meet · Flipples 定例")

    def test_block_ending_at_midnight_ends_at_1440(self):
        self.assertEqual((self.blocks[3].start, self.blocks[3].end), (1437, 1440))

    def test_timeline_text_lists_one_line_per_block(self):
        lines = ad.timeline_text(self.blocks).splitlines()
        self.assertEqual(lines[1], "13:04-15:16 · Wavebox · Meet · Flipples 定例 · https://meet.google.com/abc")
        self.assertEqual(lines[3], "23:57-00:00 · Vivaldi · night reading")

    def test_snap_keeps_range_inside_blocks(self):
        self.assertEqual(ad.snap_range("13:10-15:00", self.blocks), "13:10-15:00")

    def test_snap_moves_ends_in_gaps_to_nearest_block_edge(self):
        self.assertEqual(ad.snap_range("13:00-15:18", self.blocks), "13:04-15:16")

    def test_snap_handles_midnight(self):
        self.assertEqual(ad.snap_range("23:58-00:00", self.blocks), "23:58-00:00")

    def test_snap_accepts_en_dash_and_spaces(self):
        self.assertEqual(ad.snap_range("13:10 – 13:20", self.blocks), "13:10-13:20")

    def test_snap_rejects_garbage(self):
        self.assertIsNone(ad.snap_range("午後", self.blocks))
        self.assertIsNone(ad.snap_range("25:00-26:00", self.blocks))
        self.assertIsNone(ad.snap_range("13:10-13:20", []))

    def test_read_timeline_of_missing_day_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = make_config(Path(tmp))
            self.assertEqual(ad.read_timeline(cfg, dt.date(2026, 10, 5)), [])


MANIFEST = """---
date: 2026-10-05
ingest_apps.disposition: {apps}
ingest_messages.disposition: skipped
ingest_websites.disposition: accepted
---
"""


def write_kb(kb_dir: Path, apps: str = "accepted", missing: tuple = ()) -> None:
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "manifest.md").write_text(MANIFEST.format(apps=apps), encoding="utf-8")
    for name in ad.KB_FILES:
        if name in missing:
            continue
        body = "## Flipples\n\n第2弾の日程を確定 13:04-15:16" if name == "threads.md" else "Nothing evident."
        (kb_dir / name).write_text(f"---\ndate: 2026-10-05\nkind: kb\n---\n\n{body}\n", encoding="utf-8")


class KnowledgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kb = Path(self.tmp.name) / "KB" / "2026-10-05"

    def tearDown(self):
        self.tmp.cleanup()

    def test_ready_when_apps_accepted_and_all_files_present(self):
        write_kb(self.kb)
        self.assertTrue(ad.kb_is_ready(self.kb))

    def test_ready_when_apps_skipped(self):
        write_kb(self.kb, apps="skipped")
        self.assertTrue(ad.kb_is_ready(self.kb))

    def test_not_ready_when_any_call_rejected(self):
        write_kb(self.kb, apps='rejected: issues.md: a line carries no time range: "x"')
        self.assertFalse(ad.kb_is_ready(self.kb))

    def test_not_ready_when_a_file_is_missing(self):
        write_kb(self.kb, missing=("threads.md",))
        self.assertFalse(ad.kb_is_ready(self.kb))

    def test_not_ready_without_manifest(self):
        self.assertFalse(ad.kb_is_ready(self.kb))

    def test_read_kb_skips_empty_files_and_frontmatter(self):
        write_kb(self.kb)
        text = ad.read_kb(self.kb)
        self.assertIn("### threads.md", text)
        self.assertIn("第2弾の日程を確定 13:04-15:16", text)
        self.assertNotIn("Nothing evident.", text)
        self.assertNotIn("kind: kb", text)


class FakeAC:
    """A control socket that answers like Ambient Context and records requests."""

    def __init__(self, path: Path, reply):
        fake = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                request = json.loads(self.rfile.readline().decode("utf-8"))
                fake.requests.append(request)
                self.wfile.write((json.dumps(reply(request)) + "\n").encode("utf-8"))

        self.requests = []
        self.server = socketserver.UnixStreamServer(str(path), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def ac_reply(states, on_done=None):
    """Answers ingest_day with job-1, then job_status with the given states in order."""
    remaining = list(states)

    def reply(request):
        if request["op"] == "ingest_day":
            return {"status": "ok", "body": {"job_id": "job-1", "status": "queued"}}
        state = remaining.pop(0) if remaining else "done"
        if state == "done" and on_done:
            on_done()
        if state == "not_found":
            return {"status": "err", "body": {"code": "not_found", "message": "No job"}}
        return {"status": "ok", "body": {"id": "job-1", "status": state}}

    return reply


class EnsureKbTest(unittest.TestCase):
    def setUp(self):
        # Unix socket paths must stay under 104 bytes, so avoid the long $TMPDIR.
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.root = Path(self.tmp.name)
        self.cfg = make_config(self.root)
        self.date = dt.date(2026, 10, 5)
        self.kb = self.cfg.ac_root / "KB" / "2026-10-05"
        apps = self.cfg.ac_root / "Days" / "2026-10-05" / "apps.md"
        apps.parent.mkdir(parents=True)
        apps.write_text(APPS_MD, encoding="utf-8")
        self.fake = None

    def tearDown(self):
        if self.fake:
            self.fake.close()
        self.tmp.cleanup()

    def serve(self, reply):
        self.fake = FakeAC(self.cfg.socket, reply)

    def test_requests_ingest_and_waits_until_done(self):
        self.serve(ac_reply(["queued", "running", "done"], on_done=lambda: write_kb(self.kb)))
        self.assertTrue(ad.ensure_kb(self.cfg, self.date, sleep=lambda _: None))
        ops = [request["op"] for request in self.fake.requests]
        self.assertEqual(ops, ["ingest_day", "job_status", "job_status", "job_status"])
        self.assertEqual(self.fake.requests[0]["date"], "2026-10-05")

    def test_failed_object_status_ends_the_wait(self):
        self.serve(ac_reply([{"failed": {"stderr": "boom"}}]))
        self.assertFalse(ad.ensure_kb(self.cfg, self.date, sleep=lambda _: None))
        self.assertEqual(len(self.fake.requests), 2)

    def test_not_found_after_restart_ends_the_wait_and_trusts_the_manifest(self):
        write_kb(self.kb)
        # The manifest predates apps.md here, so a request is still made.
        os.utime(self.kb / "manifest.md", (0, 0))
        self.serve(ac_reply(["not_found"]))
        self.assertTrue(ad.ensure_kb(self.cfg, self.date, sleep=lambda _: None))
        self.assertEqual([request["op"] for request in self.fake.requests], ["ingest_day", "job_status"])

    def test_fresh_kb_needs_no_request(self):
        write_kb(self.kb)
        self.serve(ac_reply([]))
        self.assertTrue(ad.ensure_kb(self.cfg, self.date))
        self.assertEqual(self.fake.requests, [])

    def test_missing_socket_falls_back_to_existing_kb(self):
        write_kb(self.kb, apps="accepted")
        os.utime(self.kb / "manifest.md", (0, 0))
        self.assertTrue(ad.ensure_kb(self.cfg, self.date))

    def test_missing_socket_without_kb_is_not_ready(self):
        self.assertFalse(ad.ensure_kb(self.cfg, self.date))

    def test_gives_up_after_the_wait_limit(self):
        self.serve(ac_reply(["running"] * 1000))
        ticks = iter(range(0, 10_000))
        self.assertFalse(ad.ensure_kb(self.cfg, self.date, sleep=lambda _: None, clock=lambda: next(ticks)))


class VaultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def note(self, rel: str, text: str) -> None:
        path = self.vault / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_frontmatter_tags_in_every_yaml_shape(self):
        self.assertEqual(ad.frontmatter_tags(["tags:", "  - a", "- b", "title: x"]), ["a", "b"])
        self.assertEqual(ad.frontmatter_tags(["tags: [a, 'b', \"c\"]"]), ["a", "b", "c"])
        self.assertEqual(ad.frontmatter_tags(["tags: solo"]), ["solo"])
        self.assertEqual(ad.frontmatter_tags(["title: x"]), [])

    def test_vocabulary_counts_frontmatter_and_inline_tags(self):
        self.note("Magic/a.md", "---\ntags:\n  - Magic\n---\n\nbody #python\n")
        self.note("Magic/b.md", "---\ntags: [magic]\n---\n\n```\n#notatag\n```\n#ff6b6b\n")
        tags, titles = ad.vault_vocabulary(self.vault)
        self.assertEqual(tags["magic"], 2)
        self.assertEqual(tags["python"], 1)
        self.assertNotIn("notatag", tags)
        self.assertNotIn("ff6b6b", tags)
        self.assertEqual(titles, ["a", "b"])

    def test_titles_skip_daily_templates_and_dot_folders(self):
        self.note("Daily/2026-10-05.md", "x")
        self.note("Templates/for Templater/default.md", "x")
        self.note(".obsidian/plugins/x.md", "x")
        self.note("Hacking Papa/Flipples.md", "x")
        _, titles = ad.vault_vocabulary(self.vault)
        self.assertEqual(titles, ["Flipples"])


FAKE_CLAUDE = """#!/usr/bin/python3
import json, os, sys
log = os.environ["FAKE_CLAUDE_LOG"]
with open(log, "a", encoding="utf-8") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "stdin": sys.stdin.read()}) + "\\n")
mode = os.environ.get("FAKE_CLAUDE_MODE", "ok")
if mode == "garbage":
    print("Error: not logged in", file=sys.stderr)
    sys.exit(1)
payload = json.load(open(os.environ["FAKE_CLAUDE_PAYLOAD"], encoding="utf-8"))
reply = {"type": "result", "is_error": mode == "error", "result": "x", "structured_output": payload}
print(json.dumps(reply))
"""

PAYLOAD = {
    "narrative": [{"text": "午後は**Flipples**の定例で日程を詰めた", "range": "13:00-15:16"}],
    "time_use": [{"range": "13:04-15:16", "label": "Flipples 定例", "apps": ["Wavebox"]}],
    "outcomes": [{"text": "[[Flipples]] 第2弾のスケジュールを確定 #1082", "range": "13:04-15:16"}],
    "open": [{"text": "Brinno動画消失の原因調査", "range": "15:20-15:25"}],
    "tags": ["Flipples", "#video", "Bad Tag!", "daily"],
}


class FakeClaude:
    def __init__(self, root: Path, payload: dict = PAYLOAD):
        self.path = root / "fake-claude"
        self.path.write_text(FAKE_CLAUDE, encoding="utf-8")
        self.path.chmod(0o755)
        self.log = root / "claude.log"
        payload_file = root / "payload.json"
        payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.environ["FAKE_CLAUDE_LOG"] = str(self.log)
        os.environ["FAKE_CLAUDE_PAYLOAD"] = str(payload_file)
        os.environ["FAKE_CLAUDE_MODE"] = "ok"

    def calls(self) -> list:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = make_config(self.root)
        self.fake = FakeClaude(self.root)
        self.cfg.claude = str(self.fake.path)
        self.blocks = ad.parse_timeline(APPS_MD)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_prompt_fills_every_placeholder(self):
        template = "{{DATE}}|{{TIMELINE}}|{{KB}}|{{TAGS}}|{{NOTES}}"
        prompt = ad.build_prompt(
            template, dt.date(2026, 10, 5), self.blocks, "KB", Counter({"magic": 14, "aotake": 8}), ["Flipples"]
        )
        self.assertNotIn("{{", prompt)
        self.assertIn("2026-10-05|12:52-12:53 · Claude", prompt)
        self.assertIn("|KB|magic (14)\naotake (8)|Flipples", prompt)

    def test_input_hash_changes_with_kb_only_when_inputs_change(self):
        first = ad.input_hash("t", self.blocks, "kb")
        self.assertEqual(first, ad.input_hash("t", self.blocks, "kb"))
        self.assertNotEqual(first, ad.input_hash("t", self.blocks, "kb2"))
        self.assertRegex(first, r"^[0-9a-f]{16}$")

    def test_generate_returns_structured_output_and_isolates_claude(self):
        self.assertEqual(ad.generate(self.cfg, "prompt body"), PAYLOAD)
        call = self.fake.calls()[0]
        self.assertEqual(call["stdin"], "prompt body")
        for flag in ("-p", "--safe-mode", "--no-session-persistence", "--json-schema"):
            self.assertIn(flag, call["argv"])
        self.assertEqual(call["argv"][call["argv"].index("--tools") + 1], "")
        self.assertEqual(call["argv"][call["argv"].index("--model") + 1], "claude-sonnet-5")

    def test_generate_raises_on_is_error(self):
        os.environ["FAKE_CLAUDE_MODE"] = "error"
        with self.assertRaises(ad.GenerationError):
            ad.generate(self.cfg, "p")

    def test_generate_raises_on_non_json_output(self):
        os.environ["FAKE_CLAUDE_MODE"] = "garbage"
        with self.assertRaises(ad.GenerationError):
            ad.generate(self.cfg, "p")

    def test_generate_raises_when_claude_is_missing(self):
        self.cfg.claude = str(self.root / "nope")
        with self.assertRaises(ad.GenerationError):
            ad.generate(self.cfg, "p")


class NormalizeTest(unittest.TestCase):
    def setUp(self):
        self.blocks = ad.parse_timeline(APPS_MD)

    def test_clean_text(self):
        self.assertEqual(ad.clean_text("a\n  **b**  *c*"), "a b c")
        self.assertEqual(ad.clean_text("PR #1082 と #tag"), "PR \\#1082 と \\#tag")
        self.assertEqual(ad.clean_text("見た https://e.com/x。"), "見た <https://e.com/x>。")
        self.assertEqual(ad.clean_text("[x](https://e.com) <https://e.org>"), "[x](https://e.com) <https://e.org>")
        self.assertEqual(ad.clean_text("[[Flipples]] と [[壊れ"), "Flipples と 壊れ")
        self.assertEqual(ad.clean_text("[[Flipples]] 確定"), "[[Flipples]] 確定")

    def test_normalize_tags_prefers_shape_and_vocab(self):
        vocab = Counter({"keihinhyojihou": 4, "Mixed_Case": 1})
        tags = ad.normalize_tags(["Flipples", "#video", "Bad Tag!", "daily", "keihinhyojihou", "video"], vocab)
        self.assertEqual(tags, ["flipples", "video", "keihinhyojihou"])

    def test_normalize_snaps_cleans_and_drops_bad_items(self):
        raw = dict(PAYLOAD)
        raw["outcomes"] = PAYLOAD["outcomes"] + [{"text": "時刻なし", "range": "いつか"}]
        note = ad.normalize(raw, self.blocks, Counter())
        self.assertEqual(note.narrative, [("午後はFlipplesの定例で日程を詰めた", "13:04-15:16")])
        self.assertEqual(note.outcomes, [("[[Flipples]] 第2弾のスケジュールを確定 \\#1082", "13:04-15:16")])
        self.assertEqual(note.time_use, [("13:04-15:16", "Flipples 定例", ["Wavebox"])])
        self.assertEqual(note.open, [("Brinno動画消失の原因調査", "15:20-15:25")])
        self.assertEqual(note.tags, ["flipples", "video"])

    def test_normalize_fails_without_narrative_or_time_use(self):
        raw = dict(PAYLOAD, narrative=[{"text": "x", "range": "garbage"}])
        self.assertIsNone(ad.normalize(raw, self.blocks, Counter()))
        raw = dict(PAYLOAD, time_use=[])
        self.assertIsNone(ad.normalize(raw, self.blocks, Counter()))


EXPECTED_SECTION = """<!-- ambient-context:start -->
<!-- ambient-daily: in=0123456789abcdef tags=flipples,video -->

## Ambient Context

午後はFlipplesの定例で日程を詰めた 13:04-15:16

### 時間の使い方

- 13:04-15:16 Flipples 定例（Wavebox）

### 成果

- [[Flipples]] 第2弾のスケジュールを確定 \\#1082 13:04-15:16

### 未完了

- [ ] Brinno動画消失の原因調査 15:20-15:25

<!-- ambient-context:end -->"""


class RenderTest(unittest.TestCase):
    def note(self):
        return ad.normalize(PAYLOAD, ad.parse_timeline(APPS_MD), Counter())

    def test_render_section_layout(self):
        lines = ad.render_section(self.note(), "0123456789abcdef")
        self.assertEqual("\n".join(lines), EXPECTED_SECTION)

    def test_empty_optional_sections_are_left_out(self):
        note = self.note()
        note.outcomes = []
        note.open = []
        text = "\n".join(ad.render_section(note, "0" * 16))
        self.assertNotIn("### 成果", text)
        self.assertNotIn("### 未完了", text)
        self.assertTrue(text.endswith("（Wavebox）\n\n<!-- ambient-context:end -->"))

    def test_meta_line_round_trips(self):
        line = ad.render_section(self.note(), "0123456789abcdef")[1]
        match = ad.META_RE.match(line)
        self.assertEqual(match.groups(), ("0123456789abcdef", "flipples,video"))


LEGACY_NOTE = """---
created: 2026-10-05 13:02:16+09:00
modified: 2026-10-06 12:14:33+09:00
tags:
  - daily
  - ambient-context
  - personal
---

# 2026-10-01

朝のメモ。

<!-- ambient-context:start -->

## Ambient Context

Source: [Summaries/2026-10-01.md](file:///x) · generated_by: claude-opus-5

### Sessions

- old

<!-- ambient-context:end -->

夜のメモ。
"""

NOW = "2026-10-07 06:00:00+09:00"


class WriteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cfg = make_config(self.root)
        self.cfg.daily_dir.mkdir(parents=True)
        self.date = dt.date(2026, 10, 1)
        self.path = self.cfg.daily_dir / "2026-10-01.md"
        self.note = ad.normalize(PAYLOAD, ad.parse_timeline(APPS_MD), Counter())
        self.section = ad.render_section(self.note, "0123456789abcdef")

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_note_layout(self):
        text = ad.compose(None, self.date, self.section, ["flipples"], NOW, touch=True)
        head = f"---\ncreated: {NOW}\nmodified: {NOW}\ntags:\n  - daily\n  - ambient-context\n  - flipples\n---\n\n# 2026-10-01\n\n"
        self.assertTrue(text.startswith(head + "<!-- ambient-context:start -->\n"))
        self.assertTrue(text.endswith("<!-- ambient-context:end -->\n"))

    def test_legacy_note_keeps_handwriting_and_linter_keys(self):
        text = ad.compose(LEGACY_NOTE, self.date, self.section, ["flipples"], NOW, touch=True)
        self.assertIn("created: 2026-10-05 13:02:16+09:00", text)
        self.assertIn(f"modified: {NOW}", text)
        self.assertIn("  - personal\n", text)
        self.assertIn("朝のメモ。", text)
        self.assertIn("夜のメモ。", text)
        self.assertNotIn("Source:", text)
        self.assertEqual(text.count(ad.START_MARKER), 1)

    def test_only_tags_this_script_added_are_removed(self):
        first = ad.compose(LEGACY_NOTE, self.date, self.section, ["flipples", "video"], NOW, touch=True)
        second_section = ad.render_section(self.note, "fedcba9876543210")
        second_section[1] = "<!-- ambient-daily: in=fedcba9876543210 tags=flipples -->"
        second = ad.compose(first, self.date, second_section, ["flipples"], NOW, touch=True)
        self.assertNotIn("  - video\n", second)
        self.assertIn("  - personal\n", second)
        self.assertIn("  - flipples\n", second)

    def test_flow_and_unindented_tags_are_merged(self):
        flow = "---\ntags: [personal, daily]\n---\n\n# 2026-10-01\n"
        text = ad.compose(flow, self.date, self.section, ["flipples"], NOW, touch=True)
        self.assertIn("tags:\n  - personal\n  - daily\n  - ambient-context\n  - flipples\n", text)
        bare = "---\ntags:\n- personal\n---\n\n# 2026-10-01\n"
        text = ad.compose(bare, self.date, self.section, ["flipples"], NOW, touch=True)
        self.assertIn("tags:\n  - personal\n  - daily\n", text)

    def test_unbalanced_markers_raise(self):
        broken = "# 2026-10-01\n\n<!-- ambient-context:start -->\nx\n"
        with self.assertRaises(ad.MarkerError):
            ad.compose(broken, self.date, self.section, [], NOW, touch=True)

    def test_write_note_is_idempotent_and_atomic(self):
        self.assertTrue(ad.write_note(self.cfg, self.date, self.section, ["flipples"]))
        before = self.path.read_text(encoding="utf-8")
        self.assertFalse(ad.write_note(self.cfg, self.date, self.section, ["flipples"]))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)
        self.assertEqual([p.name for p in self.cfg.daily_dir.iterdir()], ["2026-10-01.md"])

    def test_dry_run_writes_nothing(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertTrue(ad.write_note(self.cfg, self.date, self.section, ["flipples"], dry_run=True))
        self.assertFalse(self.path.exists())
        self.assertIn("# 2026-10-01", out.getvalue())

    @unittest.skipUnless(shutil.which("markdownlint-cli2"), "markdownlint-cli2 not installed")
    def test_written_notes_pass_markdownlint(self):
        ad.write_note(self.cfg, self.date, self.section, ["flipples"])
        legacy = self.cfg.daily_dir / "2026-10-02.md"
        legacy.write_text(LEGACY_NOTE.replace("2026-10-01", "2026-10-02"), encoding="utf-8")
        ad.write_note(self.cfg, dt.date(2026, 10, 2), self.section, ["flipples"])
        (self.cfg.vault / ".markdownlint-cli2.jsonc").write_text('{"config":{"MD013":false}}', encoding="utf-8")
        result = subprocess.run(["markdownlint-cli2", "Daily/*.md"], cwd=self.cfg.vault, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.root = Path(self.tmp.name)
        self.cfg = make_config(self.root)
        self.fake = FakeClaude(self.root)
        self.cfg.claude = str(self.fake.path)
        self.cfg.prompt_file.write_text("{{DATE}}\n{{TIMELINE}}\n{{KB}}\n{{TAGS}}\n{{NOTES}}\n", encoding="utf-8")
        self.cfg.daily_dir.mkdir(parents=True)
        self.today = dt.date(2026, 10, 7)
        for day in ("2026-09-29", "2026-10-05", "2026-10-07"):
            apps = self.cfg.ac_root / "Days" / day / "apps.md"
            apps.parent.mkdir(parents=True)
            apps.write_text(APPS_MD, encoding="utf-8")
        write_kb(self.cfg.ac_root / "KB" / "2026-10-05")
        self.stderr = contextlib.redirect_stderr(io.StringIO())
        self.log = self.stderr.__enter__()

    def tearDown(self):
        self.stderr.__exit__(None, None, None)
        self.tmp.cleanup()

    def test_target_dates_skip_today_and_the_old(self):
        self.assertEqual(ad.target_dates(self.cfg, self.today), [dt.date(2026, 10, 5)])

    def test_generates_once_then_skips_without_calling_claude(self):
        date = dt.date(2026, 10, 5)
        self.assertEqual(ad.process_day(self.cfg, date), "generated")
        self.assertEqual(ad.process_day(self.cfg, date), "skipped")
        self.assertEqual(len(self.fake.calls()), 1)
        self.assertEqual(ad.process_day(self.cfg, date, force=True), "skipped")
        self.assertEqual(len(self.fake.calls()), 2)

    def test_prompt_carries_kb_and_vault_vocabulary(self):
        (self.cfg.vault / "Hacking Papa").mkdir(parents=True)
        (self.cfg.vault / "Hacking Papa" / "Flipples.md").write_text("---\ntags: [magic]\n---\n", encoding="utf-8")
        ad.process_day(self.cfg, dt.date(2026, 10, 5))
        stdin = self.fake.calls()[0]["stdin"]
        self.assertIn("第2弾の日程を確定 13:04-15:16", stdin)
        self.assertIn("magic (1)", stdin)
        self.assertIn("Flipples", stdin)

    def test_missing_kb_leaves_the_note_alone(self):
        date = dt.date(2026, 9, 30)
        apps = self.cfg.ac_root / "Days" / "2026-09-30" / "apps.md"
        apps.parent.mkdir(parents=True)
        apps.write_text(APPS_MD, encoding="utf-8")
        self.assertEqual(ad.process_day(self.cfg, date), "failed")
        self.assertFalse((self.cfg.daily_dir / "2026-09-30.md").exists())
        self.assertEqual(self.fake.calls(), [])

    def test_claude_failure_leaves_the_note_alone(self):
        os.environ["FAKE_CLAUDE_MODE"] = "error"
        self.assertEqual(ad.process_day(self.cfg, dt.date(2026, 10, 5)), "failed")
        self.assertFalse((self.cfg.daily_dir / "2026-10-05.md").exists())

    def test_main_logs_summary_and_returns_failure_code(self):
        self.assertEqual(ad.main([], cfg=self.cfg, today=self.today), 0)
        self.assertIn("checked 1 days, generated 1, skipped 0, failed 0", self.log.getvalue())
        os.environ["FAKE_CLAUDE_MODE"] = "error"
        self.assertEqual(ad.main(["--date", "2026-10-05", "--force"], cfg=self.cfg, today=self.today), 1)

    def test_main_exits_quietly_when_another_run_holds_the_lock(self):
        with open(self.cfg.lock_file, "w") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(ad.main([], cfg=self.cfg, today=self.today), 0)
        self.assertIn("another run is in progress", self.log.getvalue())
        self.assertEqual(self.fake.calls(), [])


class ReviewFixesTest(unittest.TestCase):
    """Regressions found by the final review."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir="/tmp")
        self.root = Path(self.tmp.name)
        self.cfg = make_config(self.root)
        self.cfg.daily_dir.mkdir(parents=True)
        self.stderr = contextlib.redirect_stderr(io.StringIO())
        self.log = self.stderr.__enter__()
        self.fake = None

    def tearDown(self):
        self.stderr.__exit__(None, None, None)
        if self.fake:
            self.fake.close()
        self.tmp.cleanup()

    def test_unexpected_error_in_one_day_is_counted_not_fatal(self):
        apps = self.cfg.ac_root / "Days" / "2026-10-05" / "apps.md"
        apps.parent.mkdir(parents=True)
        apps.write_text(APPS_MD, encoding="utf-8")
        write_kb(self.cfg.ac_root / "KB" / "2026-10-05")
        # No prompt file: process_day hits FileNotFoundError.
        self.assertEqual(ad.main([], cfg=self.cfg, today=dt.date(2026, 10, 7)), 1)
        self.assertIn("checked 1 days, generated 0, skipped 0, failed 1", self.log.getvalue())

    def test_clean_text_cannot_break_note_structure(self):
        self.assertEqual(ad.clean_text("# 見出し"), "\\# 見出し")
        self.assertEqual(ad.clean_text("> 引用"), "&gt; 引用")
        self.assertEqual(ad.clean_text("- 箇条"), "\\- 箇条")
        self.assertEqual(ad.clean_text("a<br>b <https://e.org>"), "a&lt;br&gt;b <https://e.org>")

    def test_unreadable_frontmatter_is_left_alone(self):
        broken = "---\ntitle: x\n--- \n\n# 2026-10-01\n"
        section = ad.render_section(ad.normalize(PAYLOAD, ad.parse_timeline(APPS_MD), Counter()), "0" * 16)
        with self.assertRaises(ad.MarkerError):
            ad.compose(broken, dt.date(2026, 10, 1), section, [], NOW, touch=True)

    def test_rejected_kb_is_rebuilt_with_force(self):
        apps = self.cfg.ac_root / "Days" / "2026-10-05" / "apps.md"
        apps.parent.mkdir(parents=True)
        apps.write_text(APPS_MD, encoding="utf-8")
        write_kb(self.cfg.ac_root / "KB" / "2026-10-05", apps='rejected: issues.md: "x"')
        self.fake = FakeAC(self.cfg.socket, ac_reply([]))
        ad.ensure_kb(self.cfg, dt.date(2026, 10, 5), sleep=lambda _: None)
        self.assertTrue(self.fake.requests[0]["force"])

    def test_dry_run_does_not_claim_it_wrote(self):
        apps = self.cfg.ac_root / "Days" / "2026-10-05" / "apps.md"
        apps.parent.mkdir(parents=True)
        apps.write_text(APPS_MD, encoding="utf-8")
        write_kb(self.cfg.ac_root / "KB" / "2026-10-05")
        self.cfg.prompt_file.write_text("{{TIMELINE}}", encoding="utf-8")
        self.cfg.claude = str(FakeClaude(self.root).path)
        with contextlib.redirect_stdout(io.StringIO()):
            ad.process_day(self.cfg, dt.date(2026, 10, 5), dry_run=True)
        self.assertNotIn("wrote", self.log.getvalue())
        self.assertIn("would write", self.log.getvalue())

    def test_bare_email_is_wrapped(self):
        self.assertEqual(ad.clean_text("連絡先 a.b@example.co.jp へ"), "連絡先 <a.b@example.co.jp> へ")
        self.assertEqual(ad.clean_text("<a@example.com>"), "<a@example.com>")
        self.assertEqual(ad.clean_text("https://e.com/u@x.com"), "<https://e.com/u@x.com>")

    def test_time_range_replaces_the_closing_period(self):
        raw = dict(PAYLOAD, narrative=[{"text": "定例で日程を詰めた。", "range": "13:04-15:16"}])
        note = ad.normalize(raw, ad.parse_timeline(APPS_MD), Counter())
        lines = ad.render_section(note, "0" * 16)
        self.assertIn("定例で日程を詰めた 13:04-15:16", lines)

    def test_missing_kb_is_requested_without_force(self):
        apps = self.cfg.ac_root / "Days" / "2026-10-05" / "apps.md"
        apps.parent.mkdir(parents=True)
        apps.write_text(APPS_MD, encoding="utf-8")
        self.fake = FakeAC(self.cfg.socket, ac_reply([]))
        ad.ensure_kb(self.cfg, dt.date(2026, 10, 5), sleep=lambda _: None)
        self.assertFalse(self.fake.requests[0]["force"])


class PromptFileTest(unittest.TestCase):
    def test_prompt_has_every_placeholder(self):
        text = (ROOT / "private_dot_config/ambient-daily/note-prompt.md").read_text(encoding="utf-8")
        for placeholder in ("{{DATE}}", "{{TIMELINE}}", "{{KB}}", "{{TAGS}}", "{{NOTES}}"):
            self.assertIn(placeholder, text)


if __name__ == "__main__":
    unittest.main()
