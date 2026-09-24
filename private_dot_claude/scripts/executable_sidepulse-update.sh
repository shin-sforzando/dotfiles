#!/bin/bash

set -euo pipefail

# Topgrade custom step. `sidepulse update` re-runs `sidepulse setup`, which rewrites
# the Claude Code hooks in ~/.claude/settings.json to machine-specific absolute paths.
# Topgrade's chezmoi step runs first, so the drift has to be reverted here.

SIDEPULSE="$HOME/.local/bin/sidepulse"
TARGET="$HOME/.claude/settings.json"

if [[ ! -x $SIDEPULSE ]]; then
  echo "SidePulse is not installed, skipping"
  exit 0
fi

"$SIDEPULSE" update

# Mask SidePulse hook commands on both sides so that only unrelated drift remains.
# A blind --force would also discard settings Claude Code itself wrote (e.g. permissions).
mask='(.hooks[][].hooks[]? | select(.command | test("sidepulse|hook_entry")) | .command) |= "SIDEPULSE"'
if diff -q <(jq -S "$mask" "$TARGET") <(chezmoi cat "$TARGET" | jq -S "$mask") >/dev/null; then
  chezmoi apply --force "$TARGET"
  echo "Restored portable SidePulse hooks in $TARGET"
else
  echo "$TARGET has drift beyond SidePulse hooks; review with: chezmoi diff $TARGET" >&2
  exit 1
fi
