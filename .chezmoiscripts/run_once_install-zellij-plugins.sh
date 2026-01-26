#!/bin/bash

set -e

echo "Installing Zellij plugins..."

# Create plugins directory
mkdir -p ~/.config/zellij/plugins

# Download Zoxide Session Manager plugin
echo "Downloading zsm plugin..."
curl -L https://github.com/liam-mackie/zsm/releases/latest/download/zsm.wasm \
  -o ~/.config/zellij/plugins/zsm.wasm

echo "Zellij plugins installed successfully."
