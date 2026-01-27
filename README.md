# dotfiles

<!-- Badges -->

[![Last Commit](https://img.shields.io/github/last-commit/shin-sforzando/dotfiles)](https://github.com/shin-sforzando/dotfiles/graphs/commit-activity)
[![Commitizen friendly](https://img.shields.io/badge/commitizen-friendly-brightgreen.svg)](http://commitizen.github.io/cz-cli/)

<!-- Synopsis -->

My dotfiles managed by [chezmoi](https://www.chezmoi.io/) + [Sheldon](https://sheldon.cli.rs/).

<!-- TOC -->

- [Features](#features)
- [Quick Start](#quick-start)
  - [New Machine Setup](#new-machine-setup)
  - [Manual Steps](#manual-steps)
- [Migration from Prezto](#migration-from-prezto)
- [Daily Usage](#daily-usage)
  - [Update dotfiles](#update-dotfiles)
  - [Update Sheldon plugins](#update-sheldon-plugins)
  - [Add custom aliases](#add-custom-aliases)
  - [Edit Brewfile](#edit-brewfile)
- [Key Components](#key-components)
  - [Sheldon Plugins](#sheldon-plugins)
  - [Starship Prompt](#starship-prompt)
  - [Neovim](#neovim)
- [Troubleshooting](#troubleshooting)
  - [Shell doesn't recognize commands](#shell-doesnt-recognize-commands)
  - [Plugins not loading](#plugins-not-loading)
  - [chezmoi not applying changes](#chezmoi-not-applying-changes)
- [References](#references)
- [Misc](#misc)

## Features

- **Cross-platform**: macOS (Apple Silicon) and MX Linux
- **Fast**: Sheldon-based plugin management
- **Modern**: Starship prompt, lazy.nvim, and latest CLI tools
- **Automated**: One-command setup via Homebrew / Linuxbrew

## Quick Start

### New Machine Setup

```bash
# 1. Install Homebrew (macOS) or Linuxbrew (Linux)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install chezmoi and apply dotfiles in one command
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply shin-sforzando
```

This will:

1. Install chezmoi
2. Clone this repository to `~/.local/share/chezmoi/`
3. Install Homebrew (macOS) or Linuxbrew (Linux)
4. Install all packages from Brewfile (macOS-only packages are skipped on Linux via `OS.mac?`)
5. Set up Rust, Node.js, and other tools
6. Apply all dotfiles to your home directory

### Manual Steps

After automated setup, complete these manual steps:

```bash
# 1. Set default shell
# macOS:
sudo chsh -s $(brew --prefix)/bin/zsh
# Linux:
chsh -s $(which zsh)

# 2. Set up GPG key
gpg --keyserver hkps://keys.openpgp.org --search-keys shin@sforzando.co.jp
gpg --edit-key KEYID
> trust
```

## Migration from Prezto

If you're migrating from an existing [shin-sforzando/prezto](https://github.com/shin-sforzando/prezto) setup, please refer to the detailed migration guide:

👉 **[MIGRATION.md](./MIGRATION.md)**

The guide covers:

- Step-by-step migration process
- Important backup procedures
- Common issues and solutions (.zprofile, history, etc.)
- Rollback instructions if needed

## Daily Usage

### Update dotfiles

> [!NOTE]
> Auto-commit and auto-push are enabled. Changes made via `chezmoi add`, `chezmoi edit`, or `chezmoi apply` are automatically committed and pushed.

```bash
# Edit a file
chezmoi edit ~/.zshrc

# Preview changes
chezmoi diff

# Apply changes
chezmoi apply
```

### Update Sheldon plugins

> [!NOTE]
> Sheldon plugins are automatically updated when `plugins.toml` changes via `run_onchange` script.

### Add custom aliases

Custom aliases are organized in separate files for maintainability:

```bash
# Edit or create a new alias file
chezmoi edit ~/.config/zsh/aliases/brew.zsh

# Apply changes
chezmoi apply
```

All `*.zsh` files in `~/.config/zsh/aliases/` are automatically loaded by `.zshrc`.

### Edit Brewfile

> [!IMPORTANT]
> `Brewfile` is NOT copied to `~/` to avoid accidental edits. It only exists in the chezmoi source directory.

Brewfile is a Ruby DSL. Platform-specific packages are guarded by `OS.mac?` / `OS.linux?`:

- **Common**: CLI tools shared across macOS and Linux (e.g. `bat`, `fzf`, `ripgrep`)
- **`if OS.mac?`**: macOS-only formulae (`m-cli`, `mas`, `terminal-notifier`), casks, and App Store apps
- **`if OS.linux?`**: Linux-only formulae (`libnotify`)

```bash
# Edit Brewfile
cd ~/.local/share/chezmoi
vim Brewfile

# Install/update packages
brew bundle --file=~/.local/share/chezmoi/Brewfile
```

## Key Components

### Sheldon Plugins

Only 5 essential plugins for fast startup:

- `zsh-autosuggestions` - Fish-like autosuggestions
- `zsh-completions` - Additional completion definitions
- `zsh-history-substring-search` - History search (up/down arrows)
- `zsh-you-should-use` - Reminds you to use existing aliases
- `zsh-syntax-highlighting` - Fish-like syntax highlighting

### Starship Prompt

Fast, customizable prompt with Git status, language versions, and more.

To customize: `chezmoi edit ~/.config/starship.toml`

### Neovim

Minimal configuration using lazy.nvim:

- Basic editor settings (line numbers, indentation, etc.)
- Clipboard integration
- Kanagawa color scheme
- Telescope fuzzy finder (`<leader>ff` for files, `<leader>fg` for grep)
- Treesitter for better syntax highlighting and indentation
- Claude Code integration (`<leader>ac` to toggle, `<leader>as` to send selection)
- Easy to extend with additional plugins

## Troubleshooting

### Shell doesn't recognize commands

```bash
# Reload shell configuration
source ~/.zshrc

# Or restart terminal
```

### Plugins not loading

```bash
# Update Sheldon lock file
sheldon lock --update

# Verify plugins are installed
sheldon source
```

### chezmoi not applying changes

```bash
# Check what would change
chezmoi diff

# Force apply
chezmoi apply --force
```

## References

- [chezmoi](https://www.chezmoi.io)
- [Sheldon](https://sheldon.cli.rs)
- [Starship](https://starship.rs)
- [lazy.nvim](https://lazy.folke.io)
- [topgrade](https://github.com/topgrade-rs/topgrade)

## Misc

This repository is [Commitizen](https://commitizen.github.io/cz-cli/) friendly, following [GitHub flow](https://docs.github.com/en/get-started/quickstart/github-flow).
