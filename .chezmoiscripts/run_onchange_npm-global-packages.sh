#!/bin/bash

set -eufo pipefail

# Global npm packages (edit this list to add/remove packages)
# fmt: off
NPM_GLOBAL_PACKAGES=(
  "@playwright/mcp"
  "commitizen"
  "cz-emoji"
  "happy"
  "npm-check-updates"
)
# fmt: on

if ! command -v mise &>/dev/null; then
  echo "mise not found, skipping npm global package installation"
  exit 0
fi

echo "📦 Installing global npm packages via mise..."
mise exec node -- npm install --global "${NPM_GLOBAL_PACKAGES[@]}"
echo "✅ Global npm packages installed."
