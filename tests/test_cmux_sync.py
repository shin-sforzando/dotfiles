"""Tests for dot_local/bin/executable_cmux-sync.

The script only orchestrates cmux, ghq, brctl and scutil, so every test runs it
as a subprocess with fake versions of those commands first on PATH, then
asserts on the calls they recorded and the files the script wrote.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "dot_local" / "bin" / "executable_cmux-sync"

# Calls that only read state; everything else counts as a change to cmux.
READ_ONLY_CALLS = {("workspace", "list"), ("workspace-group", "list"), ("tree",)}

FAKE_CMUX = r'''#!/usr/bin/python3
"""Fake cmux: answers from a JSON state file and records every call."""
import json
import os
import sys

state_path = os.environ["FAKE_CMUX_STATE"]
with open(state_path) as f:
    state = json.load(f)
args = sys.argv[1:]
with open(os.environ["FAKE_CMUX_CALLS"], "a") as f:
    f.write(json.dumps(args) + "\n")

key = " ".join(args[:2]) if args[:1] == ["workspace-group"] else args[0]
if key in state.get("fail_on", []):
    sys.exit(1)


def next_id(name):
    state[name] = state.get(name, 0) + 1
    with open(state_path, "w") as f:
        json.dump(state, f)
    return state[name]


if args[:2] == ["workspace", "list"]:
    print(json.dumps({"workspaces": state.get("list", [])}))
elif args[:2] == ["workspace-group", "list"]:
    print(json.dumps({"groups": state.get("groups", [])}))
elif args[:1] == ["tree"]:
    print(json.dumps(state.get("tree", {"windows": [{"workspace_count": 1}]})))
elif args[:1] == ["new-workspace"]:
    print("OK new-%d" % next_id("ws_seq"))
elif args[:2] == ["workspace-group", "create"]:
    print(json.dumps({"created": True, "group": {"ref": "grp-%d" % next_id("grp_seq")}}))
'''

FAKE_GHQ = r"""#!/bin/sh
case "$1" in
  root) printf '%s\n' "$FAKE_GHQ_ROOT" ;;
  get)
    printf '%s\n' "$2" >>"$FAKE_GHQ_CALLS"
    for fail in $FAKE_GHQ_FAIL; do [ "$2" = "$fail" ] && exit 1; done
    # A private repo without stored credentials makes git wait for a password on the
    # terminal unless prompting is disabled, which is what hung real pulls
    for private in $FAKE_GHQ_PRIVATE; do
      if [ "$2" = "$private" ]; then
        case "$GIT_TERMINAL_PROMPT:$GIT_SSH_COMMAND" in
          0:*BatchMode=yes*) exit 128 ;;
          *) sleep 30; exit 1 ;;
        esac
      fi
    done
    mkdir -p "$FAKE_GHQ_ROOT/$2"
    ;;
esac
"""

# Simulates iCloud finishing a download by copying the staged file into place.
FAKE_BRCTL = r"""#!/bin/sh
[ "$1" = download ] && [ -n "$FAKE_BRCTL_SOURCE" ] && cp "$FAKE_BRCTL_SOURCE" "$2"
exit 0
"""

FAKE_SCUTIL = r"""#!/bin/sh
printf '%s\n' "${FAKE_HOSTNAME:-TestMac}"
"""


def workspace(
    index: int,
    cwd: str | None,
    *,
    ws_id: str | None = None,
    ws_ref: str | None = None,
    title: str | None = None,
    color: str | None = None,
    pinned: bool = False,
    selected: bool = False,
    description: str | None = None,
    remote: bool = False,
) -> dict:
    """Builds one element of the fake `cmux workspace list --json` output.

    Args:
        index: Sidebar position reported by cmux.
        cwd: Absolute current directory, or None when cmux reports none.
        ws_id: Workspace UUID; defaults to "old-<index>".
        ws_ref: Workspace ref that group membership refers to; defaults to "workspace:<index>".
        title: Custom title, or None when the workspace was never renamed.
        color: Custom sidebar color.
        pinned: Whether the workspace is pinned.
        selected: Whether the workspace is the selected one.
        description: Custom description.
        remote: Whether the workspace is an SSH or cloud VM session.

    Returns:
        A dict shaped like cmux 0.65.1's JSON for one workspace.
    """
    return {
        "id": ws_id or f"old-{index}",
        "ref": ws_ref or f"workspace:{index}",
        "index": index,
        "current_directory": cwd,
        "title": "auto",
        "custom_title": title,
        "has_custom_title": title is not None,
        "custom_color": color,
        "pinned": pinned,
        "selected": selected,
        "description": description,
        "remote": {"enabled": remote},
    }


def make_snapshot(
    workspaces: list[dict],
    groups: list[dict] | None = None,
    *,
    host: str = "MacStudio",
    version: int = 1,
) -> dict:
    """Builds a snapshot.json payload with defaults for every workspace field.

    Args:
        workspaces: Partial workspace entries; missing fields get neutral defaults.
        groups: Group entries, if any.
        host: Host name recorded as the snapshot's origin.
        version: Snapshot schema version.

    Returns:
        A dict in the snapshot.json format described in the spec.
    """
    defaults = {
        "title": None,
        "color": None,
        "repo": None,
        "group": None,
        "pinned": False,
        "description": None,
        "selected": False,
    }
    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": version,
        "createdAt": created,
        "host": host,
        "groups": groups or [],
        "workspaces": [{**defaults, **w} for w in workspaces],
    }


class CmuxSyncTestCase(unittest.TestCase):
    """Runs cmux-sync inside a throwaway HOME with fake external commands."""

    def setUp(self) -> None:
        """Creates the temporary HOME, ghq root, iCloud dir and fake commands."""
        # Resolved because /var is a symlink to /private/var and git reports real paths
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.ghq_root = self.home / "Workspace"
        self.ghq_root.mkdir(parents=True)
        self.sync_dir = self.tmp / "icloud"
        self.state_dir = self.tmp / "state"
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        fakes = {
            "cmux": FAKE_CMUX,
            "ghq": FAKE_GHQ,
            "brctl": FAKE_BRCTL,
            "scutil": FAKE_SCUTIL,
        }
        for name, body in fakes.items():
            path = bin_dir / name
            path.write_text(body)
            path.chmod(0o755)
        self.cmux_state = self.tmp / "cmux-state.json"
        self.cmux_calls_file = self.tmp / "cmux-calls.jsonl"
        self.ghq_calls_file = self.tmp / "ghq-calls.txt"
        self.set_cmux_state(list=[])
        self.env = {
            "PATH": f"{bin_dir}:/opt/homebrew/bin:/usr/bin:/bin",
            "HOME": str(self.home),
            "CMUX_SYNC_DIR": str(self.sync_dir),
            "CMUX_SYNC_STATE_DIR": str(self.state_dir),
            "CMUX_SYNC_DOWNLOAD_TIMEOUT": "2",
            "FAKE_CMUX_STATE": str(self.cmux_state),
            "FAKE_CMUX_CALLS": str(self.cmux_calls_file),
            "FAKE_GHQ_ROOT": str(self.ghq_root),
            "FAKE_GHQ_CALLS": str(self.ghq_calls_file),
        }

    def set_cmux_state(self, **state: object) -> None:
        """Replaces what the fake cmux reports.

        Args:
            **state: Keys "list", "groups", "tree" and "fail_on" (a list of
                commands such as "reorder-workspaces" that should exit 1).
        """
        self.cmux_state.write_text(json.dumps(state))

    def run_sync(self, *args: str, stdin: str = "", env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        """Runs cmux-sync with the fake environment.

        Args:
            *args: Arguments passed to cmux-sync.
            stdin: Text fed to the script's standard input.
            env: Extra environment variables layered over the defaults.

        Returns:
            The completed process with captured text stdout and stderr.
        """
        return subprocess.run(
            ["/bin/bash", str(SCRIPT), *args],
            input=stdin,
            capture_output=True,
            text=True,
            env={**self.env, **(env or {})},
            check=False,
            # A hung git prompt must fail the test, not stall the suite
            timeout=15,
        )

    def cmux_calls(self) -> list[list[str]]:
        """Returns every argv the fake cmux received, in call order."""
        if not self.cmux_calls_file.exists():
            return []
        return [json.loads(line) for line in self.cmux_calls_file.read_text().splitlines()]

    def mutating_calls(self) -> list[list[str]]:
        """Returns the calls that change cmux state, skipping reads and notify."""
        return [
            call
            for call in self.cmux_calls()
            if tuple(call[:2]) not in READ_ONLY_CALLS
            and tuple(call[:1]) not in READ_ONLY_CALLS
            and call[:1] != ["notify"]
        ]

    def write_snapshot(self, snapshot: dict) -> Path:
        """Writes a snapshot into the fake iCloud directory.

        Args:
            snapshot: Payload produced by make_snapshot.

        Returns:
            Path of the written snapshot.json.
        """
        self.sync_dir.mkdir(parents=True, exist_ok=True)
        path = self.sync_dir / "snapshot.json"
        path.write_text(json.dumps(snapshot))
        return path

    def snapshot(self) -> dict:
        """Returns the snapshot.json the script wrote."""
        return json.loads((self.sync_dir / "snapshot.json").read_text())


class CommandLineTest(CmuxSyncTestCase):
    """Argument handling shared by every subcommand."""

    def test_unknown_command_exits_with_usage(self) -> None:
        """An unknown subcommand prints usage and exits 2."""
        result = self.run_sync("frobnicate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage: cmux-sync", result.stderr)


class ShowTest(CmuxSyncTestCase):
    """cmux-sync show."""

    def test_show_summarizes_snapshot(self) -> None:
        """Show prints the origin, counts, titles and group names."""
        self.write_snapshot(
            make_snapshot(
                [
                    {"title": "PaperTalk", "cwd": "~/Workspace/a", "group": "g1", "selected": True},
                    {"cwd": "~/Workspace/b"},
                ],
                [{"key": "g1", "name": "sforzando", "color": None, "icon": None, "collapsed": False}],
            )
        )
        result = self.run_sync("show")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("from MacStudio", result.stdout)
        self.assertIn("2 workspaces, 1 groups", result.stdout)
        self.assertIn("* PaperTalk  ~/Workspace/a  [sforzando]", result.stdout)
        self.assertIn("(auto title)  ~/Workspace/b", result.stdout)
        self.assertEqual(self.mutating_calls(), [])

    def test_show_downloads_icloud_placeholder(self) -> None:
        """A not-yet-downloaded snapshot is fetched with brctl before reading."""
        staged = self.tmp / "staged.json"
        staged.write_text(json.dumps(make_snapshot([{"cwd": "~"}])))
        self.sync_dir.mkdir(parents=True)
        (self.sync_dir / ".snapshot.json.icloud").write_text("")
        result = self.run_sync("show", env={"FAKE_BRCTL_SOURCE": str(staged)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 workspaces", result.stdout)

    def test_show_without_snapshot_points_to_push(self) -> None:
        """Show fails with a hint when no snapshot exists yet."""
        result = self.run_sync("show")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run 'cmux-sync push'", result.stderr)


class PushTest(CmuxSyncTestCase):
    """cmux-sync push."""

    def test_push_keeps_only_custom_titles(self) -> None:
        """Auto titles are dropped so the receiving Mac regenerates them."""
        self.set_cmux_state(
            list=[
                workspace(0, str(self.home), title="Renamed"),
                workspace(1, str(self.home)),
            ]
        )
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        titles = [w["title"] for w in self.snapshot()["workspaces"]]
        self.assertEqual(titles, ["Renamed", None])

    def test_push_orders_by_index(self) -> None:
        """Workspaces are stored in sidebar order even if cmux lists them otherwise."""
        self.set_cmux_state(
            list=[
                workspace(1, str(self.home), title="second"),
                workspace(0, str(self.home), title="first"),
            ]
        )
        self.run_sync("push")
        titles = [w["title"] for w in self.snapshot()["workspaces"]]
        self.assertEqual(titles, ["first", "second"])

    def test_push_stores_tilde_cwd_and_ghq_repo(self) -> None:
        """Paths are stored relative to HOME and ghq checkouts get a repo slug."""
        repo_sub = self.ghq_root / "github.com" / "o" / "r" / "sub dir"
        repo_sub.mkdir(parents=True)
        spaced = self.home / "Library" / "Mobile Documents"
        spaced.mkdir(parents=True)
        self.set_cmux_state(list=[workspace(0, str(repo_sub)), workspace(1, str(spaced))])
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        first, second = self.snapshot()["workspaces"]
        self.assertEqual(first["cwd"], "~/Workspace/github.com/o/r/sub dir")
        self.assertEqual(first["repo"], "github.com/o/r")
        self.assertEqual(second["cwd"], "~/Library/Mobile Documents")
        self.assertIsNone(second["repo"])

    def test_push_resolves_worktree_outside_ghq_root(self) -> None:
        """A worktree outside the ghq root maps back to its main clone's slug."""
        main = self.ghq_root / "github.com" / "o" / "wt"
        main.mkdir(parents=True)
        git = ["git", "-C", str(main), "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "init"], check=True)
        worktree = self.home / "worktrees" / "feature"
        subprocess.run([*git, "worktree", "add", "-q", str(worktree)], check=True)
        self.set_cmux_state(list=[workspace(0, str(worktree))])
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot()["workspaces"][0]["repo"], "github.com/o/wt")

    def test_push_excludes_remote_workspaces(self) -> None:
        """SSH and cloud VM workspaces are skipped with a warning."""
        self.set_cmux_state(list=[workspace(0, str(self.home)), workspace(1, str(self.home), remote=True)])
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.snapshot()["workspaces"]), 1)
        self.assertIn("skipping 1 remote workspace", result.stderr)

    def test_push_warns_when_several_windows_have_workspaces(self) -> None:
        """Only the current window is captured, and the user is told so."""
        self.set_cmux_state(
            list=[workspace(0, str(self.home))],
            tree={"windows": [{"workspace_count": 1}, {"workspace_count": 3}]},
        )
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 windows have workspaces", result.stderr)

    def test_push_notifies_the_result(self) -> None:
        """Push reports through cmux notify, since a palette run closes its tab."""
        self.set_cmux_state(list=[workspace(0, str(self.home))])
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        notices = [c for c in self.cmux_calls() if c[:1] == ["notify"]]
        self.assertEqual(len(notices), 1)
        self.assertIn("pushed 1 workspaces and 0 groups from TestMac", notices[0])

    def test_push_keeps_workspace_without_directory(self) -> None:
        """A workspace with no reported directory is stored with a null cwd."""
        self.set_cmux_state(list=[workspace(0, None), workspace(1, str(self.home))])
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        first, second = self.snapshot()["workspaces"]
        self.assertIsNone(first["cwd"])
        self.assertIsNone(first["repo"])
        self.assertEqual(second["cwd"], "~")

    def test_push_records_groups_and_workspace_attributes(self) -> None:
        """Group membership, colors, icon, pin, description and selection survive."""
        self.set_cmux_state(
            list=[
                workspace(0, str(self.home), ws_ref="a", color="#E63946", pinned=True),
                workspace(1, str(self.home), ws_ref="b", description="notes", selected=True),
            ],
            groups=[
                {
                    "ref": "G",
                    "name": "sforzando",
                    "member_workspace_refs": ["a", "b"],
                    "custom_color": "#457B9D",
                    "icon_symbol": "folder.fill",
                    "is_collapsed": True,
                }
            ],
        )
        result = self.run_sync("push")
        self.assertEqual(result.returncode, 0, result.stderr)
        snap = self.snapshot()
        self.assertEqual(snap["version"], 1)
        self.assertEqual(snap["host"], "TestMac")
        self.assertEqual(
            snap["groups"],
            [
                {
                    "key": "g1",
                    "name": "sforzando",
                    "color": "#457B9D",
                    "icon": "folder.fill",
                    "collapsed": True,
                }
            ],
        )
        first, second = snap["workspaces"]
        self.assertEqual((first["group"], first["color"], first["pinned"]), ("g1", "#E63946", True))
        self.assertEqual((second["description"], second["selected"]), ("notes", True))
        self.assertEqual(self.mutating_calls(), [])


class PullTest(CmuxSyncTestCase):
    """cmux-sync pull."""

    def setUp(self) -> None:
        """Gives the receiving Mac three open workspaces, the middle one running pull."""
        super().setUp()
        self.set_cmux_state(list=[workspace(i, str(self.home)) for i in range(3)])
        self.env["CMUX_WORKSPACE_ID"] = "old-1"

    def creates(self) -> list[list[str]]:
        """Returns the new-workspace calls in order."""
        return [c for c in self.cmux_calls() if c[:1] == ["new-workspace"]]

    @staticmethod
    def flag(call: list[str], name: str) -> str | None:
        """Returns the value that follows a flag in one recorded call.

        Args:
            call: One recorded argv.
            name: Flag such as "--cwd".

        Returns:
            The flag's value, or None when the flag is absent.
        """
        return call[call.index(name) + 1] if name in call else None

    def test_pull_rejects_unknown_version(self) -> None:
        """A snapshot from a newer schema is refused before touching anything."""
        self.write_snapshot(make_snapshot([{"cwd": "~"}], version=2))
        result = self.run_sync("pull", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version 2 is not supported", result.stderr)
        self.assertEqual(self.mutating_calls(), [])

    def test_pull_rejects_empty_snapshot(self) -> None:
        """An empty snapshot would close everything, so it is refused."""
        self.write_snapshot(make_snapshot([]))
        result = self.run_sync("pull", "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to close everything", result.stderr)
        self.assertEqual(self.mutating_calls(), [])

    def test_pull_stops_when_answer_is_not_yes(self) -> None:
        """Without --yes, anything but y leaves cmux untouched."""
        self.write_snapshot(make_snapshot([{"cwd": "~"}]))
        for answer in ("n\n", ""):
            result = self.run_sync("pull", stdin=answer)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("aborted", result.stderr)
        self.assertEqual(self.mutating_calls(), [])

    def test_pull_dry_run_resolves_cwds_without_side_effects(self) -> None:
        """Dry run shows each resolved directory and pending clone, changing nothing."""
        exists = self.ghq_root / "github.com" / "o" / "here"
        exists.mkdir(parents=True)
        main_only = self.ghq_root / "github.com" / "o" / "main"
        main_only.mkdir(parents=True)
        self.write_snapshot(
            make_snapshot(
                [
                    {"cwd": "~/Workspace/github.com/o/here", "repo": "github.com/o/here"},
                    {"cwd": "~/worktrees/main-feature", "repo": "github.com/o/main"},
                    {"cwd": "~/Workspace/github.com/o/new", "repo": "github.com/o/new"},
                    {"cwd": "~/gone/deeper"},
                ]
            )
        )
        result = self.run_sync("pull", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"at {exists}", result.stdout)
        self.assertIn(f"at {main_only}", result.stdout)
        self.assertIn("would clone github.com/o/new", result.stdout)
        self.assertIn(f"at {self.ghq_root}/github.com/o/new", result.stdout)
        self.assertIn(f"at {self.home}\n", result.stdout)
        self.assertEqual(self.mutating_calls(), [])
        self.assertFalse(self.ghq_calls_file.exists())

    def test_pull_creates_everything_before_closing_and_closes_caller_last(self) -> None:
        """Old workspaces close only after creation, and the caller closes last."""
        self.write_snapshot(make_snapshot([{"cwd": "~", "selected": True}, {"cwd": "~"}]))
        result = self.run_sync("pull", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.mutating_calls()
        kinds = [c[0] for c in calls]
        first_close = kinds.index("close-workspace")
        self.assertNotIn("new-workspace", kinds[first_close:])
        self.assertIn(["reorder-workspaces", "--order", "new-1,new-2"], calls[:first_close])
        closes = [self.flag(c, "--workspace") for c in calls if c[0] == "close-workspace"]
        self.assertEqual(closes, ["old-0", "old-2", "old-1"])
        self.assertEqual(calls[-1], ["close-workspace", "--workspace", "old-1", "--force"])
        self.assertIn(["select-workspace", "--workspace", "new-1"], calls)

    def test_pull_applies_workspace_attributes(self) -> None:
        """Title, description, color and pin reach cmux unchanged."""
        tricky = 'Paper "Talk" \'s'
        self.write_snapshot(
            make_snapshot(
                [
                    {
                        "cwd": "~",
                        "title": tricky,
                        "description": "d e",
                        "color": "#E63946",
                        "pinned": True,
                    },
                    {"cwd": "~"},
                ]
            )
        )
        result = self.run_sync("pull", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        first, second = self.creates()
        self.assertEqual(self.flag(first, "--cwd"), str(self.home))
        self.assertEqual(self.flag(first, "--name"), tricky)
        self.assertEqual(self.flag(first, "--description"), "d e")
        self.assertIsNone(self.flag(second, "--name"))
        calls = self.cmux_calls()
        self.assertIn(
            ["workspace-action", "--action", "set-color", "--workspace", "new-1", "--color", "#E63946"],
            calls,
        )
        self.assertIn(["workspace-action", "--action", "pin", "--workspace", "new-1"], calls)

    def test_pull_keeps_paths_with_spaces_whole(self) -> None:
        """A cwd with spaces is passed as one argument."""
        spaced = self.home / "Library" / "Mobile Documents"
        spaced.mkdir(parents=True)
        self.write_snapshot(make_snapshot([{"cwd": "~/Library/Mobile Documents"}]))
        result = self.run_sync("pull", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.flag(self.creates()[0], "--cwd"), str(spaced))

    def test_pull_builds_groups_with_a_fresh_key_each_run(self) -> None:
        """Groups get their members, look, and a per-run idempotency key."""
        groups = [{"key": "g1", "name": "sfz", "color": "#457B9D", "icon": "folder.fill", "collapsed": True}]
        self.write_snapshot(
            make_snapshot(
                [{"cwd": "~", "group": "g1"}, {"cwd": "~"}, {"cwd": "~", "group": "g1"}],
                groups,
            )
        )
        keys = []
        for _ in range(2):
            self.cmux_calls_file.unlink(missing_ok=True)
            self.set_cmux_state(list=[workspace(i, str(self.home)) for i in range(3)])
            result = self.run_sync("pull", "--yes")
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = self.cmux_calls()
            create = next(c for c in calls if c[:2] == ["workspace-group", "create"])
            self.assertEqual(self.flag(create, "--from"), "new-1,new-3")
            self.assertEqual(self.flag(create, "--name"), "sfz")
            keys.append(self.flag(create, "--idempotency-key"))
            self.assertIn(["workspace-group", "set-color", "grp-1", "--hex", "#457B9D"], calls)
            self.assertIn(["workspace-group", "set-icon", "grp-1", "--symbol", "folder.fill"], calls)
            self.assertIn(["workspace-group", "collapse", "grp-1"], calls)
        self.assertNotEqual(keys[0], keys[1])

    def test_pull_does_not_wait_for_git_credentials(self) -> None:
        """A clone that needs a password fails fast and falls back to the parent."""
        self.write_snapshot(make_snapshot([{"cwd": "~/Workspace/github.com/o/secret", "repo": "github.com/o/secret"}]))
        result = self.run_sync("pull", "--yes", env={"FAKE_GHQ_PRIVATE": "github.com/o/secret"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.flag(self.creates()[0], "--cwd"), str(self.ghq_root))
        log = (self.state_dir / "last-pull.log").read_text()
        self.assertIn("clone failed: github.com/o/secret", log)

    def test_pull_clones_missing_repos_and_falls_back_on_failure(self) -> None:
        """Missing repos are cloned; a failed clone opens at the nearest parent."""
        self.write_snapshot(
            make_snapshot(
                [
                    {"cwd": "~/Workspace/github.com/o/ok", "repo": "github.com/o/ok"},
                    {"cwd": "~/Workspace/github.com/o/bad", "repo": "github.com/o/bad"},
                ]
            )
        )
        result = self.run_sync("pull", "--yes", env={"FAKE_GHQ_FAIL": "github.com/o/bad"})
        self.assertEqual(result.returncode, 0, result.stderr)
        ok, bad = self.creates()
        self.assertEqual(self.flag(ok, "--cwd"), f"{self.ghq_root}/github.com/o/ok")
        # github.com/o exists because the sibling clone succeeded
        self.assertEqual(self.flag(bad, "--cwd"), f"{self.ghq_root}/github.com/o")
        log = (self.state_dir / "last-pull.log").read_text()
        self.assertIn("clone failed: github.com/o/bad", log)

    def test_pull_closes_nothing_when_reordering_fails(self) -> None:
        """A failure before the close phase leaves every old workspace open."""
        self.write_snapshot(make_snapshot([{"cwd": "~"}]))
        self.set_cmux_state(
            list=[workspace(i, str(self.home)) for i in range(3)],
            fail_on=["reorder-workspaces"],
        )
        result = self.run_sync("pull", "--yes")
        self.assertNotEqual(result.returncode, 0)
        kinds = [c[0] for c in self.mutating_calls()]
        self.assertNotIn("close-workspace", kinds)
        log = (self.state_dir / "last-pull.log").read_text()
        self.assertIn("previous workspaces are untouched", log)
        self.assertIn("new-1", log)

    def test_pull_opens_workspace_without_directory_at_home(self) -> None:
        """A null cwd from the snapshot opens at HOME instead of a relative path."""
        self.write_snapshot(make_snapshot([{"cwd": None}]))
        result = self.run_sync("pull", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.flag(self.creates()[0], "--cwd"), str(self.home))

    def test_pull_logs_workspaces_it_could_not_close(self) -> None:
        """Close failures reach the log, which outlives the caller's terminal."""
        self.write_snapshot(make_snapshot([{"cwd": "~"}]))
        self.set_cmux_state(
            list=[workspace(i, str(self.home)) for i in range(3)],
            fail_on=["close-workspace"],
        )
        self.run_sync("pull", "--yes")
        log = (self.state_dir / "last-pull.log").read_text()
        self.assertIn("could not close workspace old-0", log)
        self.assertIn("could not close workspace old-2", log)

    def test_pull_keeps_the_previous_backup(self) -> None:
        """A second pull moves the earlier backup aside instead of overwriting it."""
        self.state_dir.mkdir(parents=True)
        earlier = {"version": 1, "marker": "earlier layout"}
        (self.state_dir / "before-pull.json").write_text(json.dumps(earlier))
        self.write_snapshot(make_snapshot([{"cwd": "~"}]))
        result = self.run_sync("pull", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        previous = json.loads((self.state_dir / "before-pull.prev.json").read_text())
        self.assertEqual(previous, earlier)

    def test_pull_saves_current_layout_before_changing_it(self) -> None:
        """The receiving Mac's layout is saved and can be pulled back with --from."""
        self.write_snapshot(make_snapshot([{"cwd": "~"}]))
        result = self.run_sync("pull", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        backup = json.loads((self.state_dir / "before-pull.json").read_text())
        self.assertEqual(len(backup["workspaces"]), 3)
        restore = self.run_sync("pull", "--dry-run", "--from", str(self.state_dir / "before-pull.json"))
        self.assertEqual(restore.returncode, 0, restore.stderr)


if __name__ == "__main__":
    unittest.main()
