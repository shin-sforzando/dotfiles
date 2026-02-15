# Migration Guide: Prezto to chezmoi + Sheldon

このガイドは、[shin-sforzando/prezto](https://github.com/shin-sforzando/prezto)で環境構築済みのマシンを、このchezmoiベースの環境に移行する手順をまとめたものです。

> [!NOTE]
> このガイドは **Preztoからの移行専用** です。
> ゼロからのセットアップは [README.md](./README.md) の Quick Start セクションを参照してください。

- [前提条件](#前提条件)
- [Stage 1: バックアップ](#stage-1-バックアップ)
- [Stage 2: 必要なツールのインストール](#stage-2-必要なツールのインストール)
- [Stage 3: このリポジトリのセットアップ](#stage-3-このリポジトリのセットアップ)
  - [方法A: 段階的なセットアップ（推奨）](#方法a-段階的なセットアップ推奨)
  - [方法B: ワンコマンドセットアップ](#方法b-ワンコマンドセットアップ)
- [Stage 4: パッケージのインストール](#stage-4-パッケージのインストール)
  - [Manual Steps（必須）](#manual-steps必須)
- [Stage 5: 動作確認](#stage-5-動作確認)
  - [確認すべき項目](#確認すべき項目)
- [Stage 6: Preztoの削除](#stage-6-preztoの削除)
- [Stage 7: トラブルシューティング](#stage-7-トラブルシューティング)
  - [コマンド履歴が保存されない](#コマンド履歴が保存されない)
  - [PATHが通らない（brewコマンドが見つからない）](#pathが通らないbrewコマンドが見つからない)
  - [Prezto設定ファイルの移行漏れ](#prezto設定ファイルの移行漏れ)
  - [シェル補完が機能しない](#シェル補完が機能しない)
  - [`.zprofile`適用時に競合エラー](#zprofile適用時に競合エラー)
  - [Sheldonが見つからない（Linux環境）](#sheldonが見つからないlinux環境)
  - [Starshipプロンプトが表示されない](#starshipプロンプトが表示されない)
  - [GPG/SSH鍵の設定エラー](#gpgssh鍵の設定エラー)
  - [Node.jsバージョン管理ツールとの競合](#nodejsバージョン管理ツールとの競合)
  - [カスタムaliasの移行](#カスタムaliasの移行)
- [よくある質問](#よくある質問)
  - [Q: 移行前の環境に戻したい場合は？](#q-移行前の環境に戻したい場合は)
  - [Q: 一部のファイルだけchezmoiで管理したい](#q-一部のファイルだけchezmoiで管理したい)
- [参考リンク](#参考リンク)

## 前提条件

- macOS（Apple Silicon） or MX Linux
- Homebrew（macOS）またはLinuxbrew（Linux）がインストール済み
- Gitが使用可能
- インターネット接続

## Stage 1: バックアップ

移行前に、重要なファイルをバックアップします。

```bash
# コマンド履歴をバックアップ
cp ~/.zsh_history ~/.zsh_history.backup

# 現在のzsh設定ファイルを確認
ls -la ~/ | grep "^l.*\.z"  # シンボリックリンクを確認
ls -la ~/.config/           # 設定ディレクトリを確認

# Prezto独自の設定があればバックアップ
if [ -f ~/.zpreztorc ]; then
  cp ~/.zpreztorc ~/.zpreztorc.backup
fi
```

## Stage 2: 必要なツールのインストール

```bash
# Homebrew (macOS) / Linuxbrew (Linux) のインストール（未導入の場合）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# chezmoiのインストール
brew install chezmoi

# Sheldonのインストール
brew install sheldon

# その他の推奨ツール（まだの場合）
brew install starship fastfetch
```

## Stage 3: このリポジトリのセットアップ

### 方法A: 段階的なセットアップ（推奨）

移行の際は、各ステップを確認しながら進めることを推奨します。

```bash
# chezmoiでこのリポジトリを初期化
chezmoi init https://github.com/shin-sforzando/dotfiles.git

# 変更内容を確認（まだ適用しない）
chezmoi diff

# 問題なければ適用
chezmoi apply
```

**⚠️ 重要**: `chezmoi apply`時に「.zprofile has changed」などの警告が出た場合:

1. `diff`を入力して差分を確認
2. 問題なければ`a` (all-overwrite)で適用

### 方法B: ワンコマンドセットアップ

以下のコマンドで Stage 2〜4 を一括実行できます。

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply shin-sforzando
```

このコマンドは chezmoi のインストール、リポジトリのクローン、パッケージのインストール、dotfiles の適用を自動で行います。

> [!WARNING]
> ワンコマンドセットアップを使用する場合でも、**Stage 1のバックアップは必ず実施してください**。

## Stage 4: パッケージのインストール

> [!NOTE]
> `chezmoi apply` 実行時に `run_once_before_install-packages.sh.tmpl` が自動実行され、
> Homebrew、Brewfile、Rust、Python、Node.js等のパッケージが自動インストールされます。
> 以下の手動コマンドは、自動実行が失敗した場合のみ必要です。

```bash
# Brewfileからパッケージを一括インストール（必要に応じて）
cd ~/.local/share/chezmoi
brew bundle

# Sheldonプラグインの初期化（必要に応じて）
sheldon lock --update
```

### Manual Steps（必須）

自動セットアップ完了後、以下の手動設定を実施してください：

```bash
# 1. デフォルトシェルの変更
# macOS:
sudo chsh -s $(brew --prefix)/bin/zsh

# Linux:
chsh -s $(which zsh)

# 2. GPG鍵の設定
gpg --keyserver hkps://keys.openpgp.org --search-keys shin@sforzando.co.jp
gpg --edit-key KEYID
> trust
> 5 (I trust ultimately)
> quit
```

> [!IMPORTANT]
> デフォルトシェル変更後は、**一度ログアウト**してから次のStageに進んでください。

## Stage 5: 動作確認

新しいシェルを起動して、すべてが正常に動作するか確認します。

```bash
# 新しいシェルを起動
exec zsh

# fastfetchが表示されるか確認（ログイン時）
# Starshipプロンプトが表示されるか確認

# PATHが正しく設定されているか
echo $PATH
which brew

# コマンド履歴が機能するか
history
```

### 確認すべき項目

**基本動作:**

- [ ] fastfetchがログイン時に表示される
- [ ] Starshipプロンプトが正しく表示される（ホスト名含む）
- [ ] `brew`コマンドが使える
- [ ] コマンド履歴が保存される（新しいコマンドを入力後、`history`で確認）
- [ ] 補完が機能する（`git <Tab>`など）
- [ ] 環境変数が正しく設定されている（`echo $EDITOR`など）

**GPG・SSH:**

- [ ] GPG Agent / SSH Agent が正常に動作する（`ssh-add -L`で鍵が表示される）
- [ ] GPG鍵が正しく信頼されている（`gpg --list-keys`で確認）

**ツール動作:**

- [ ] direnvが有効（direnv使用プロジェクトで `cd` した際に環境変数がロードされる）
- [ ] fzfが動作する（`Ctrl+R` で履歴検索、`Ctrl+J` でディレクトリ移動）
- [ ] zoxide (`cd`) が正常に動作する
- [ ] yazi (`y` コマンド) が利用可能

## Stage 6: Preztoの削除

**⚠️ 警告**: この段階に進む前に、必ずStage 5の動作確認をすべて完了してください。

```bash
# Preztoのシンボリックリンクを削除
# （chezmoi管理下のファイルに置き換わっているはず）
ls -la ~/ | grep "^l.*\.z"  # 残っているシンボリックリンクを確認

# 残っているシンボリックリンクがあれば削除
# rm ~/.zshrc ~/.zlogin ~/.zlogout  # など（必要に応じて）

# Preztoディレクトリを削除
# ⚠️ 最終確認: 本当に削除して良いか再確認してください
rm -rf ~/.zprezto

# 念のため、もう一度新しいシェルで確認
exec zsh
```

## Stage 7: トラブルシューティング

### コマンド履歴が保存されない

**症状**: 新しいコマンドを入力しても、シェルを再起動すると履歴が消える

**原因**: `~/.zshrc`に履歴設定が含まれていない

**解決方法**: chezmoiの最新版を取得して再適用

```bash
cd ~/.local/share/chezmoi
git pull
chezmoi apply
exec zsh
```

履歴設定は`dot_zshrc`の以下の部分で行われています。

```zsh
HISTFILE="${ZDOTDIR:-$HOME}/.zsh_history"
HISTSIZE=10000
SAVEHIST=10000
setopt SHARE_HISTORY
# ... その他の履歴オプション
```

### PATHが通らない（brewコマンドが見つからない）

**症状**: `brew: command not found`などのエラー

**原因**: `~/.zprofile`が欠落している、またはHomebrew初期化が実行されていない

```bash
# .zprofileが存在するか確認
ls -la ~/.zprofile

# 存在しない場合
cd ~/.local/share/chezmoi
chezmoi apply ~/.zprofile

# 新しいシェルで確認
exec zsh
echo $PATH
```

`.zprofile`には以下の重要な設定が含まれています。

- Homebrew初期化（`brew shellenv`）
- PATH設定
- EDITOR/VISUAL/PAGER設定

### Prezto設定ファイルの移行漏れ

**症状**: Preztoの`dot_config_dir/`配下にあった設定ファイルが移行されていない

```bash
# Preztoのdot_config_dirを確認
ls -la ~/.zprezto/dot_config_dir/

# 必要なファイルがchezmoiで管理されているか確認
ls -la ~/.local/share/chezmoi/private_dot_config/
```

**主な移行候補**:

- `topgrade.toml` - システム更新設定
- `direnv/direnv.toml` - direnv設定
- `ghostty/config` - Ghosttyターミナル設定
- `ov/config.yaml` - ovページャー設定

### シェル補完が機能しない

**症状**: `git <Tab>`などで補完が効かない

**原因**: Sheldonプラグインが正しくロードされていない、または補完ファイルが生成されていない

```bash
# Sheldonプラグインを更新
sheldon lock --update

# 補完ディレクトリを確認
ls -la ~/.zsh_completions/

# 新しいシェルで確認
exec zsh
```

### `.zprofile`適用時に競合エラー

**症状**: `chezmoi apply`で「.zprofile has changed」と表示される

1. `diff`を入力して差分を確認
2. chezmoi管理下の内容で問題なければ、`overwrite`または`a` (all-overwrite)を選択
3. Preztoのシンボリックリンクが残っている場合は削除:

   ```bash
   rm ~/.zprofile  # シンボリックリンクの場合のみ
   chezmoi apply
   ```

### Sheldonが見つからない（Linux環境）

**症状**: `sheldon: command not found`

**原因**: BrewfileでSheldonがインストールされたが、PATHが即座に反映されていない

```bash
# シェルを再起動
exec zsh

# それでも見つからない場合は手動でインストール
brew install sheldon
```

### Starshipプロンプトが表示されない

**症状**: シェル起動後もStarshipプロンプトが表示されず、デフォルトプロンプトのまま

**原因**: Starshipがインストールされていないか、`.zshrc`の初期化が実行されていない

```bash
# Starshipがインストールされているか確認
which starship

# インストールされていない場合
brew install starship

# .zshrcを再読み込み
source ~/.zshrc

# それでも表示されない場合
exec zsh
```

### GPG/SSH鍵の設定エラー

**症状**: シェル起動時に `gpgconf not found` や SSH認証が機能しない

**原因**: GPGがインストールされていない、またはGPG Agentの設定が不完全

```bash
# GPGのインストール確認
which gpg

# インストールされていない場合
brew install gnupg

# GPG Agentの再起動
gpgconf --kill gpg-agent
gpg-agent --daemon

# SSH鍵の確認
ssh-add -L
```

### Node.jsバージョン管理ツールとの競合

**症状**: Preztoでnodenv/nvmを使用していたが、Voltaに移行したい

**解決方法**: 既存のNode.jsバージョン管理ツールをアンインストールしてから、Voltaで再設定

```bash
# nodenvの削除（使用していた場合）
brew uninstall nodenv
rm -rf ~/.nodenv

# nvmの削除（使用していた場合）
rm -rf ~/.nvm

# .zshrcからnodenv/nvmの設定を削除（自動的に削除されているはず）
# 新しいシェルでVoltaを確認
exec zsh
volta --version

# Node.jsのインストール（必要に応じて）
volta install node@lts
```

### カスタムaliasの移行

**症状**: Preztoで使用していた独自のaliasが移行されていない

**解決方法**: カスタムaliasを `~/.config/zsh/aliases/` に追加

```bash
# 新しいaliasファイルを作成
chezmoi edit ~/.config/zsh/aliases/custom.zsh

# 以下のようにaliasを追加
# alias myalias="command"

# 適用
chezmoi apply

# 確認
source ~/.zshrc
alias | grep myalias
```

> [!TIP]
> より詳細なトラブルシューティングは [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) を参照してください。

## よくある質問

### Q: 移行前の環境に戻したい場合は？

**A**: 以下の手順でPrezto環境に復元できます。

```bash
# 1. chezmoi管理ファイルの削除
chezmoi purge  # ⚠️ 全管理ファイルを削除（確認プロンプトあり）

# 2. Preztoのシンボリックリンクを再作成
cd ~/.zprezto
./install.sh

# 3. 履歴を復元
cp ~/.zsh_history.backup ~/.zsh_history

# 4. 新しいシェルで確認
exec zsh
```

> [!WARNING]
> `chezmoi purge` は chezmoi が管理しているすべてのファイルを削除します。
> 実行前に必ず確認してください。

### Q: 一部のファイルだけchezmoiで管理したい

**A**: `.chezmoiignore` で除外設定が可能です。

```bash
# .chezmoiignoreを編集
chezmoi edit ~/.local/share/chezmoi/.chezmoiignore

# 特定のファイルを除外（例: .zshrc_localなど）
echo ".zshrc_local" >> ~/.local/share/chezmoi/.chezmoiignore
```

## 参考リンク

- [chezmoi公式ドキュメント](https://www.chezmoi.io/)
- [Sheldon公式ドキュメント](https://sheldon.cli.rs/)
- [Starship公式ドキュメント](https://starship.rs/)
- [元のPrezto設定](https://github.com/shin-sforzando/prezto)
