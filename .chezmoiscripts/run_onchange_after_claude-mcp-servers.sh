#!/bin/bash

set -eufo pipefail

# Claude Code stores user-scoped MCP servers in ~/.claude.json, which .chezmoiignore
# deliberately excludes because that file also holds the OAuth session and per-project
# state. The `mcpServers` key in settings.json is NOT read by Claude Code — an entry
# placed there never appears in `claude mcp list` — so the CLI is the only supported
# write path, and this script is how the declarations survive in the chezmoi source.
#
# run_onchange keys off this file's own contents, so editing a server definition below
# is what re-triggers registration.

if ! command -v claude &>/dev/null; then
  echo "⚠️  claude not found, skipping MCP server registration"
  exit 0
fi

# Remove-then-add rather than a "does it exist?" guard: `claude mcp get` exits non-zero
# for plugin-provided servers too, so it cannot tell "absent" from "present", and the
# unconditional path also converges when a definition below changes.
register() {
  local name="$1"
  shift
  echo "🔌 Registering MCP server '${name}'..."
  claude mcp remove --scope user "${name}" &>/dev/null || true
  claude mcp add --scope user "${name}" -- "$@"
}

# drawio: search_shapes resolves the official draw.io stencil styles (GCP, Cisco,
# Kubernetes, AWS, …) that the drawio plugin skill is written to call out to. Without
# it the skill falls back to labelled rectangles. Binary comes from mise (@drawio/mcp).
register drawio drawio-mcp

echo "✅ Claude Code MCP servers registered."
