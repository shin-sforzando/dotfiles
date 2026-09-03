#!/bin/bash

set -eufo pipefail

# gh extensions to keep installed. Editing this list changes the script's own
# content hash, which is what re-triggers run_onchange -- so unlike the sheldon
# and mise scripts there is no external `include ... | sha256sum` line here.
EXTENSIONS=(
  # PR / Issue / notification dashboard TUI
  dlvhdr/gh-dash
  # Stacked PR workflow; the gh-stack skill assumes this extension is present
  github/gh-stack
  # Block until a GitHub Actions run finishes
  k1LoW/gh-wait
)

# github/gh-copilot is installed on this machine but deliberately not declared
# here, so it stays manually managed rather than being restored everywhere.

if ! command -v gh &>/dev/null; then
  echo "⚠️  gh not found, skipping extension installation"
  exit 0
fi

# A fresh machine runs `chezmoi apply` before `gh auth login`, and every
# extension operation hits the API. Skip rather than fail the whole apply.
if ! gh auth status &>/dev/null; then
  echo "⚠️  gh is not authenticated, skipping extension installation"
  echo "    Run 'gh auth login', then 'chezmoi apply' again."
  exit 0
fi

installed="$(gh extension list || true)"

for ext in "${EXTENSIONS[@]}"; do
  if grep -qF "${ext}" <<<"${installed}"; then
    echo "🔄 Upgrading ${ext}..."
    gh extension upgrade "${ext##*/}"
  else
    echo "📦 Installing ${ext}..."
    gh extension install "${ext}"
  fi
done

echo "✅ gh extensions ready."
