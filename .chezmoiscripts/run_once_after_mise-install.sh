#!/bin/bash

set -eufo pipefail

if ! command -v mise &>/dev/null; then
  echo "mise not found, skipping"
  exit 0
fi

echo "⚡ Installing tools via mise (node LTS and others defined in config.toml)..."
mise install
echo "✅ mise tools installed."
