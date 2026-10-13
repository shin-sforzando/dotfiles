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
    cwd: str,
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
        cwd: Absolute current directory of the workspace.
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


if __name__ == "__main__":
    unittest.main()
