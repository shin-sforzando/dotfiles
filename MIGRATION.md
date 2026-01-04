# Migration Guide: Prezto to chezmoi + Sheldon

このガイドは、[shin-sforzando/prezto](https://github.com/shin-sforzando/prezto)で環境構築済みのマシンを、このchezmoiベースの環境に移行する手順をまとめたものです。

- [前提条件](#前提条件)
- [Stage 1: バックアップ](#stage-1-バックアップ)
- [Stage 2: 必要なツールのインストール](#stage-2-必要なツールのインストール)
- [Stage 3: このリポジトリのセットアップ](#stage-3-このリポジトリのセットアップ)
- [Stage 4: パッケージのインストール](#stage-4-パッケージのインストール)
- [Stage 5: 動作確認](#stage-5-動作確認)
  - [確認すべき項目](#確認すべき項目)
- [Stage 6: Preztoの削除](#stage-6-preztoの削除)
- [Stage 7: トラブルシューティング](#stage-7-トラブルシューティング)
  - [コマンド履歴が保存されない](#コマンド履歴が保存されない)
  - [PATHが通らない（brewコマンドが見つからない）](#pathが通らないbrewコマンドが見つからない)
  - [Prezto設定ファイルの移行漏れ](#prezto設定ファイルの移行漏れ)
  - [シェル補完が機能しない](#シェル補完が機能しない)
  - [`.zprofile`適用時に競合エラー](#zprofile適用時に競合エラー)
- [よくある質問](#よくある質問)
  - [Q: 移行前の環境に戻したい場合は？](#q-移行前の環境に戻したい場合は)
- [参考リンク](#参考リンク)

## 前提条件

- macOS（Apple SiliconまたはIntel）
- Homebrewがインストール済み
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
# chezmoiのインストール
brew install chezmoi

# Sheldonのインストール
brew install sheldon

# その他の推奨ツール（まだの場合）
brew install starship fastfetch
```

## Stage 3: このリポジトリのセットアップ

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

## Stage 4: パッケージのインストール

```bash
# Brewfileからパッケージを一括インストール
# （chezmoi applyでBrewfileは配置済み）
cd ~/.local/share/chezmoi
brew bundle

# Sheldonプラグインの初期化
sheldon lock --update
```

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

- [ ] fastfetchがログイン時に表示される
- [ ] Starshipプロンプトが正しく表示される（ホスト名含む）
- [ ] `brew`コマンドが使える
- [ ] コマンド履歴が保存される（新しいコマンドを入力後、`history`で確認）
- [ ] 補完が機能する（`git <Tab>`など）
- [ ] 環境変数が正しく設定されている（`echo $EDITOR`など）

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

## よくある質問

### Q: 移行前の環境に戻したい場合は？

**A**: バックアップから復元できます。

```bash
# Preztoのシンボリックリンクを再作成
cd ~/.zprezto
./install.sh

# 履歴を復元
cp ~/.zsh_history.backup ~/.zsh_history
```

## 参考リンク

- [chezmoi公式ドキュメント](https://www.chezmoi.io/)
- [Sheldon公式ドキュメント](https://sheldon.cli.rs/)
- [Starship公式ドキュメント](https://starship.rs/)
- [元のPrezto設定](https://github.com/shin-sforzando/prezto)
