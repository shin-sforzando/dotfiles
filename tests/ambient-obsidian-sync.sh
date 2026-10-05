#!/bin/bash
#
# Scenario tests for dot_local/bin/executable_ambient-obsidian-sync.
#
# Runs under /bin/bash 3.2 on purpose: launchd runs the script with the system
# bash and BSD awk, and two bugs found so far (heredoc parsing and locale
# collation) only reproduce there. Needs markdownlint-cli2 on PATH because a
# lint-clean daily note is one of the requirements.
#
# Usage: /bin/bash tests/ambient-obsidian-sync.sh [path-to-script]

# The assertion helpers are only ever called through check "${@:2}", an
# indirect call the linter cannot follow.
# shellcheck disable=SC2329
set -u

here=$(cd "$(dirname "$0")/.." && pwd)
SCRIPT="${1:-$here/dot_local/bin/executable_ambient-obsidian-sync}"
ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT
export AMBIENT_SUMMARIES_DIR="$ROOT/Summaries" OBSIDIAN_DAILY_DIR="$ROOT/Daily"
export AMBIENT_SYNC_NOTIFY=0
mkdir -p "$AMBIENT_SUMMARIES_DIR" "$OBSIDIAN_DAILY_DIR"
# Same rules as the vault's own .markdownlint-cli2.jsonc.
printf '{ "config": { "MD013": false, "MD060": false } }\n' >"$ROOT/.markdownlint-cli2.jsonc"

fail=0
pass() { echo "ok   - $1"; }
flunk() {
  echo "FAIL - $1"
  fail=1
}
check() { if "${@:2}"; then pass "$1"; else flunk "$1"; fi; }
has_line() { grep -qxF -- "$2" "$1"; }
has_text() { grep -qF -- "$2" "$1"; }
count_lines() { grep -cxF -- "$2" "$1"; }
run_sync() { /bin/bash "$SCRIPT" 2>/dev/null; }
lint() {
  [ -f "$OBSIDIAN_DAILY_DIR/$1" ] || return 1
  (cd "$ROOT" && markdownlint-cli2 "Daily/$1" >/dev/null 2>&1) && return 0
  (cd "$ROOT" && markdownlint-cli2 "Daily/$1" 2>&1 | grep -E 'MD[0-9]' | sed 's/^/       /')
  return 1
}

# Deliberately messy, the way models actually write it.
cat >"$AMBIENT_SUMMARIES_DIR/2026-10-01.md" <<'EOF'
---
date: 2026-10-01
type: day-context
generated_by: claude-sonnet-5
tags: [Flipples, claude, "#ffmpeg"]
---

# Day title

午前は会議だった。午後は実装した（14:00-15:00）。夜は休んだ。
---
## Sessions
- **09:00-10:00** 会議。議事録を書いた。
- 10:00-11:00 PR #1082がmainにマージされた。
## Key references
- doc (https://example.com/a/b) と https://example.org/x
- `code # not a tag。 not split。` 終わり。
```
# not a heading。 not split。
```
## Reasoning
理由は*ない*。**強調**も不要。
EOF

# 1. Missing note: frontmatter tags, H1 date, cleaned section.
run_sync
N="$OBSIDIAN_DAILY_DIR/2026-10-01.md"
check "creates missing note" test -f "$N"
check "frontmatter first" test "$(head -1 "$N")" = "---"
check "fixed tag daily" has_line "$N" "  - daily"
check "fixed tag ambient-context" has_line "$N" "  - ambient-context"
check "summary tag lowercased" has_line "$N" "  - flipples"
check "summary tag hash stripped" has_line "$N" "  - ffmpeg"
check "h1 date" has_line "$N" "# 2026-10-01"
check "h2 fixed name" has_line "$N" "## Ambient Context"
check "summary h1 becomes plain line" has_line "$N" "Day title"
check "sections at h3" has_line "$N" "### Sessions"
check "summary frontmatter dropped" test "$(count_lines "$N" "type: day-context")" = 0
check "sentence split" has_line "$N" "午前は会議だった。"
check "closing bracket kept with sentence" has_line "$N" "午後は実装した（14:00-15:00）。"
check "list continuation indented" has_line "$N" "  議事録を書いた。"
check "horizontal rule removed" test "$(count_lines "$N" "---")" = 2
check "bold stripped" test "$(grep -c '\*\*' "$N")" = 0
check "italic stripped" has_line "$N" "理由はない。"
check "tag escaped" has_text "$N" 'PR \#1082'
check "bare url in parens wrapped" has_text "$N" "(<https://example.com/a/b>)"
check "bare url wrapped" has_text "$N" "<https://example.org/x>"
# shellcheck disable=SC2016 # The backticks are literal Markdown, not a substitution.
check "inline code untouched" has_text "$N" '`code # not a tag。 not split。` 終わり。'
check "fence untouched" has_line "$N" "# not a heading。 not split。"
check "markdownlint clean" lint 2026-10-01.md

# 2. Unchanged input leaves the file untouched.
before=$(stat -f %m "$N")
sleep 1
/bin/bash "$SCRIPT" 2>"$ROOT/run.log"
check "idempotent no rewrite" test "$(stat -f %m "$N")" = "$before"
# A no-op run must still leave a trace, or the log cannot tell it from a run that never happened.
check "no-op run logs a summary line" grep -q 'checked 1 summaries, updated 0, failed 0' "$ROOT/run.log"

# 3. Handwritten content and own tags survive a summary change.
awk 'NR == 2 { print "created: 2026-10-01"; print "tags:"; print "  - personal"; next } /^tags:$/ { skip = 1; next } skip && /^  - / { next } { skip = 0; print }' "$N" >"$N.tmp" && mv "$N.tmp" "$N"
awk '/^# 2026-10-01$/ { print; print ""; print "朝のメモ。"; next } { print }' "$N" >"$N.tmp" && mv "$N.tmp" "$N"
printf '\n夜のメモ。\n' >>"$N"
sed -i '' 's/夜は休んだ。/夜は読書した。/' "$AMBIENT_SUMMARIES_DIR/2026-10-01.md"
run_sync
check "summary change applied" has_line "$N" "夜は読書した。"
check "old sentence replaced" test "$(count_lines "$N" "夜は休んだ。")" = 0
check "own frontmatter key kept" has_line "$N" "created: 2026-10-01"
check "own tag kept" has_line "$N" "  - personal"
check "fixed tag merged once" test "$(count_lines "$N" "  - daily")" = 1
check "memo before kept" has_line "$N" "朝のメモ。"
check "memo after kept" has_line "$N" "夜のメモ。"
check "single section" test "$(grep -c 'ambient-context:start' "$N")" = 1
check "markdownlint clean after merge" lint 2026-10-01.md

# 4. Existing note without frontmatter or markers gets both.
P="$OBSIDIAN_DAILY_DIR/2026-10-02.md"
printf '# 2026-10-02\n\nonly memo\n' >"$P"
sed 's/2026-10-01/2026-10-02/' "$AMBIENT_SUMMARIES_DIR/2026-10-01.md" >"$AMBIENT_SUMMARIES_DIR/2026-10-02.md"
run_sync
check "frontmatter prepended" test "$(head -1 "$P")" = "---"
check "tags added to plain note" has_line "$P" "  - daily"
check "memo kept before section" awk '/only memo/ { m = NR } /^## Ambient Context$/ { s = NR } END { exit !(m && s && m < s) }' "$P"
check "no duplicate h1" test "$(count_lines "$P" "# 2026-10-02")" = 1
check "markdownlint clean on append" lint 2026-10-02.md

# 5. Broken markers fail loudly and leave the note alone.
B="$OBSIDIAN_DAILY_DIR/2026-10-03.md"
printf 'x\n<!-- ambient-context:start -->\ny\n' >"$B"
cp "$AMBIENT_SUMMARIES_DIR/2026-10-01.md" "$AMBIENT_SUMMARIES_DIR/2026-10-03.md"
run_sync
rc=$?
check "broken markers exit nonzero" test "$rc" -ne 0
check "broken note untouched" test "$(cat "$B")" = "$(printf 'x\n<!-- ambient-context:start -->\ny')"
rm "$AMBIENT_SUMMARIES_DIR/2026-10-03.md"

# 6. Summaries older than the age window are skipped.
cp "$AMBIENT_SUMMARIES_DIR/2026-10-01.md" "$AMBIENT_SUMMARIES_DIR/2026-09-01.md"
touch -t 202609010000 "$AMBIENT_SUMMARIES_DIR/2026-09-01.md"
run_sync
check "old summary skipped" test ! -f "$OBSIDIAN_DAILY_DIR/2026-09-01.md"

# 7. No stray temp files left in the vault.
check "no temp files" test -z "$(find "$OBSIDIAN_DAILY_DIR" -name '.ambient-sync.*')"

exit "$fail"
