# dotfiles

<!-- Badges -->

[![Last Commit](https://img.shields.io/github/last-commit/shin-sforzando/dotfiles)](https://github.com/shin-sforzando/dotfiles/graphs/commit-activity)
[![Commitizen friendly](https://img.shields.io/badge/commitizen-friendly-brightgreen.svg)](http://commitizen.github.io/cz-cli/)
[![managed with chezmoi](https://img.shields.io/badge/managed%20with-chezmoi-blue)](https://www.chezmoi.io/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)](https://github.com/shin-sforzando/dotfiles)

<!-- Synopsis -->

My dotfiles managed by [chezmoi](https://www.chezmoi.io/) + [Sheldon](https://sheldon.cli.rs/).

<!-- TOC -->

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [New Machine Setup](#new-machine-setup)
    - [Install Homebrew](#install-homebrew)
    - [Init with chezmoi](#init-with-chezmoi)
  - [Manual Steps](#manual-steps)
- [Daily Usage](#daily-usage)
  - [Update dotfiles](#update-dotfiles)
  - [Update Sheldon plugins](#update-sheldon-plugins)
  - [Add custom aliases](#add-custom-aliases)
  - [Edit Brewfile](#edit-brewfile)
  - [Pre-commit hooks](#pre-commit-hooks)
- [Key Components](#key-components)
  - [Managed Configurations](#managed-configurations)
  - [Sheldon Plugins](#sheldon-plugins)
  - [Starship Prompt](#starship-prompt)
  - [Neovim](#neovim)
- [Troubleshooting](#troubleshooting)
- [References](#references)
- [Misc](#misc)

## Features

- **Cross-platform**: macOS (Apple Silicon) and MX Linux
- **Fast**: Sheldon-based plugin management
- **Modern**: Starship prompt, lazy.nvim, and latest CLI tools
- **Automated**: One-command setup via Homebrew / Linuxbrew

## Prerequisites

Before starting, ensure you have:

- **Operating System**: macOS (Apple Silicon) or MX Linux
- **Shell**: Zsh (macOS default; install on Linux if needed)
- **Tools**: Git, curl
- **Network**: Internet connection for package installation
- **Permissions**: Sudo access for shell and package manager setup

## Quick Start

### New Machine Setup

> [!NOTE]
> Please perform the following steps in Zsh.
> macOS now defaults to Zsh, but Linux does not necessarily default to Zsh.

#### Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Init with chezmoi

```bash
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

# 3. Log in to Atuin for shell history sync
atuin login --key "$(op read "op://Personal/Atuin Key/key")"
atuin sync

# 4. Set up Tailscale SSH
# macOS: if a GUI Tailscale.app was installed, uninstall it first (and remove
#        its System Extension) so OSS tailscaled (from Brewfile) owns the TUN.
#        The macOS services script auto-runs `brew services start tailscale`.
# Advertise Tailscale SSH (browser auth; re-mention existing non-default flags):
sudo tailscale up --ssh
# Tip: set the SSH rule (autogroup:member -> autogroup:self) to action:accept
#      in the admin console to skip the periodic check-mode re-auth.
# Pitfalls: see TROUBLESHOOTING.md "Tailscale / SSH".

# 5. Enable git hooks (Lefthook) in the chezmoi source repo
# The lefthook binary is installed via Brewfile, but hooks must be activated once per clone.
cd ~/.local/share/chezmoi
lefthook install
```

> [!NOTE]
> The encryption key is stored in 1Password ("Atuin Key" item) and retrieved via the `op` CLI.
> On the first machine, save your key to 1Password with: `atuin key | op item create --category Password --title "Atuin Key" --field "key[concealed]=$(cat)"`

## Daily Usage

### Update dotfiles

> [!NOTE]
> Auto-commit and auto-push are enabled via chezmoi's `git.autoCommit` and `git.autoPush` settings.
> Changes made via `chezmoi add`, `chezmoi edit`, or `chezmoi apply` are automatically committed and pushed to the remote repository.
> This ensures your dotfiles are always backed up and synchronized across machines.

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
> `Brewfile` is NOT copied to `~/` to avoid accidental edits.
> It only exists in the chezmoi source directory.

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

### Pre-commit hooks

> [!NOTE]
> This repo uses [Lefthook](https://lefthook.dev/) (`lefthook.yml`) to keep commits clean.
> Activate the hooks once per clone with `lefthook install` (see [Manual Steps](#manual-steps)).

On each commit, the `pre-commit` hook:

- Sorts the Claude permission allowlist in `.claude/settings.local.json` (`jq`)
- Formats shell scripts with `shfmt`
- Lints Markdown (`markdownlint-cli2`) and validates JSON (`jq`)

## Key Components

### Managed Configurations

This repository manages configurations for the following applications:

| Tool         | Description                             | Config Path                                |
| ------------ | --------------------------------------- | ------------------------------------------ |
| **Ghostty**  | GPU-accelerated terminal emulator       | `~/.config/ghostty/`                       |
| **Helix**    | Post-modern modal text editor           | `~/.config/helix/`                         |
| **Neovim**   | Vim-fork with lazy.nvim plugin manager  | `~/.config/nvim/`                          |
| **Zed**      | High-performance, AI-native code editor | `~/.config/zed/`                           |
| **Zellij**   | Terminal workspace and multiplexer      | `~/.config/zellij/`                        |
| **Yazi**     | Blazing fast terminal file manager      | `~/.config/yazi/` (auto-installs packages) |
| **direnv**   | Per-directory environment variables     | `~/.config/direnv/`                        |
| **ov**       | Feature-rich terminal pager             | `~/.config/ov/`                            |
| **Starship** | Cross-shell prompt                      | `~/.config/starship.toml`                  |
| **Sheldon**  | Fast Zsh plugin manager                 | `~/.config/sheldon/`                       |
| **topgrade** | System update manager                   | `~/.config/topgrade.toml`                  |
| **Atuin**    | Shell history sync (E2E encrypted)      | `~/.config/atuin/`                         |
| **SSH**      | Tailscale SSH host aliases (keyless)    | `~/.ssh/config`                            |

> [!NOTE]
> Yazi plugins are automatically installed/updated via `run_onchange` script when `package.toml` changes.
>
> SSH uses [Tailscale SSH](https://tailscale.com/kb/1193/tailscale-ssh) (keyless, by
> Tailscale node identity). `HostName` entries use Tailscale IPs (100.x) instead of
> MagicDNS names — see [Troubleshooting](./TROUBLESHOOTING.md#tailscale--ssh) for why.

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

For comprehensive troubleshooting, see **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)**.

**Quick fixes:**

- **Shell doesn't recognize commands**: `source ~/.zshrc` or restart terminal
- **Plugins not loading**: `sheldon lock --update` and `exec zsh`
- **chezmoi not applying changes**: `chezmoi diff` then `chezmoi apply --force`
- **PATH not working**: Check `~/.zprofile` exists and run `exec zsh`
- **GPG/SSH issues**: `gpgconf --kill gpg-agent` then `exec zsh`

**Common issues:**

- [Initial setup problems](./TROUBLESHOOTING.md#初期セットアップ)
- [Shell and prompt issues](./TROUBLESHOOTING.md#シェルプロンプト)
- [chezmoi-specific problems](./TROUBLESHOOTING.md#chezmoi)
- [GPG/SSH/YubiKey setup](./TROUBLESHOOTING.md#gpgsshyubikey)

## References

- [chezmoi](https://www.chezmoi.io) - Manage your dotfiles across multiple machines
- [Sheldon](https://sheldon.cli.rs) - Fast, configurable shell plugin manager
- [Starship](https://starship.rs) - Cross-shell prompt
- [Ghostty](https://ghostty.org) - GPU-accelerated terminal emulator
- [Helix](https://helix-editor.com) - Post-modern modal text editor
- [Neovim](https://neovim.io) - Hyperextensible Vim-based text editor
- [lazy.nvim](https://lazy.folke.io) - Modern plugin manager for Neovim
- [Zed](https://zed.dev) - High-performance, multiplayer code editor
- [Zellij](https://zellij.dev) - Terminal workspace and multiplexer
- [Yazi](https://yazi-rs.github.io) - Blazing fast terminal file manager
- [direnv](https://direnv.net) - Unclutter your .profile
- [ov](https://noborus.github.io/ov/) - Feature-rich terminal pager
- [topgrade](https://github.com/topgrade-rs/topgrade) - Upgrade all the things
- [Atuin](https://atuin.sh) - Magical shell history sync
- [Lefthook](https://lefthook.dev) - Fast and powerful Git hooks manager

## Misc

This repository is [Commitizen](https://commitizen.github.io/cz-cli/) friendly, following [GitHub flow](https://docs.github.com/en/get-started/quickstart/github-flow).
