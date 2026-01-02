#!/bin/bash
set -eufo pipefail

# Sheldon plugins.toml hash: {{ include "private_dot_config/sheldon/plugins.toml" | sha256sum }}

if command -v sheldon &>/dev/null; then
  echo "🔌 Updating Sheldon plugins..."
  sheldon lock --update
  echo "✅ Sheldon plugins updated!"
else
  echo "⚠️  sheldon not found, skipping plugin update"
fi
