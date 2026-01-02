# dotfiles

Modern dotfiles managed by [chezmoi](https://www.chezmoi.io/) + [Sheldon](https://sheldon.cli.rs/).

- [Features](#features)
- [Quick Start](#quick-start)
  - [New Machine Setup](#new-machine-setup)
  - [Manual Steps](#manual-steps)
- [Daily Usage](#daily-usage)
  - [Update dotfiles](#update-dotfiles)
  - [Commit and push](#commit-and-push)
  - [Update plugins](#update-plugins)
- [Structure](#structure)
- [Key Components](#key-components)
  - [Sheldon Plugins](#sheldon-plugins)
  - [Starship Prompt](#starship-prompt)
  - [Neovim](#neovim)
- [Troubleshooting](#troubleshooting)
  - [Shell doesn't recognize commands](#shell-doesnt-recognize-commands)
  - [Plugins not loading](#plugins-not-loading)
  - [chezmoi not applying changes](#chezmoi-not-applying-changes)

## Features

- **Fast**: Sheldon-based plugin management with only 4 core plugins
- **Modern**: Starship prompt, lazy.nvim, and latest CLI tools
- **Automated**: One-command setup for new machines

## Quick Start

### New Machine Setup

```bash
# Install chezmoi and apply dotfiles in one command
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply <your-github-username>
```

This will:

1. Install chezmoi
2. Clone this repository to `~/.local/share/chezmoi/`
3. Install Homebrew (if needed)
4. Install all packages from Brewfile
5. Set up Rust, Node.js, and other tools
6. Apply all dotfiles to your home directory

### Manual Steps

After automated setup, complete these manual steps:

```bash
# 1. Set default shell
sudo chsh -s $(brew --prefix)/bin/zsh

# 2. Set up GPG key
gpg --keyserver hkps://keys.openpgp.org --search-keys shin@sforzando.co.jp
gpg --edit-key KEYID
> trust
```

## Daily Usage

### Update dotfiles

```bash
# Edit a file
chezmoi edit ~/.zshrc

# Preview changes
chezmoi diff

# Apply changes
chezmoi apply
```

### Edit Brewfile

**Important:** `Brewfile` is NOT copied to `~/` to avoid accidental edits. It only exists in the chezmoi source directory.

```bash
# Edit Brewfile
cd ~/.local/share/chezmoi
vim Brewfile

# Install/update packages
brew bundle --file=~/.local/share/chezmoi/Brewfile

# Or use chezmoi shortcut
chezmoi cd
vim Brewfile
brew bundle
```

### Commit and push

```bash
cd ~/.local/share/chezmoi
git add .
git commit -m "Update zsh config"
git push
```

### Update plugins

```bash
# Update Sheldon plugins
sheldon lock --update

# Update Homebrew packages
brew update && brew upgrade
```

## Structure

```plain
~/.local/share/chezmoi/
├── .chezmoiignore              # Files to exclude from sync
├── .chezmoiscripts/            # Automated setup scripts
│   └── run_once_before_install-packages.sh
├── dot_zshrc                   # ~/.zshrc
├── dot_zshenv                  # ~/.zshenv
├── dot_zprofile                # ~/.zprofile
├── dot_gitconfig               # ~/.gitconfig
├── dot_gitignore               # ~/.gitignore
├── dot_czrc                    # ~/.czrc (commitizen config)
├── Brewfile                    # Homebrew packages (NOT copied to ~/, edit here only)
├── private_dot_config/         # ~/.config/
│   ├── sheldon/plugins.toml    # Zsh plugin definitions
│   ├── ghostty/config          # Ghostty terminal config
│   ├── direnv/direnv.toml      # direnv config
│   ├── ov/config.yaml          # ov pager config
│   └── nvim/                   # Neovim config (lazy.nvim)
├── private_dot_claude/         # ~/.claude/
│   ├── settings.json           # Claude Code settings
│   └── executable_notify.sh    # Completion notification script
└── dot_local/bin/              # ~/.local/bin/
    └── executable_wt           # Git worktree manager
```

## Key Components

### Sheldon Plugins

Only 4 essential plugins for fast startup:

- `zsh-autosuggestions` - Fish-like autosuggestions
- `zsh-completions` - Additional completion definitions
- `zsh-history-substring-search` - History search (up/down arrows)
- `zsh-syntax-highlighting` - Fish-like syntax highlighting

### Starship Prompt

Fast, customizable prompt with Git status, language versions, and more.

To customize: `chezmoi edit ~/.config/starship.toml`

### Neovim

Minimal configuration using lazy.nvim:

- Basic editor settings (line numbers, indentation, etc.)
- Clipboard integration
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
