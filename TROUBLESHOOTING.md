# トラブルシューティング

このドキュメントは、dotfiles環境で発生する一般的な問題と解決方法をまとめたものです。

**目的別ガイド:**

- **初めてのセットアップ**: [初期セットアップ](#初期セットアップ)
- **Preztoからの移行**: [MIGRATION.md](./MIGRATION.md) の Stage 7
- **日常的な問題**: [シェル・プロンプト](#シェルプロンプト)、[chezmoi](#chezmoi)
- **環境診断**: [診断コマンド集](#診断コマンド集)

<!-- TOC -->

- [初期セットアップ](#初期セットアップ)
  - [Homebrewのインストールに失敗する](#homebrewのインストールに失敗する)
  - [chezmoi initが途中で止まる](#chezmoi-initが途中で止まる)
  - [run\_onceスクリプトが失敗した場合の再実行](#run_onceスクリプトが失敗した場合の再実行)
  - [デフォルトシェルの変更](#デフォルトシェルの変更)
- [シェル・プロンプト](#シェルプロンプト)
  - [コマンドが見つからない（PATH問題）](#コマンドが見つからないpath問題)
  - [Sheldonプラグインが読み込まれない](#sheldonプラグインが読み込まれない)
  - [Starshipプロンプトが表示されない](#starshipプロンプトが表示されない)
  - [コマンド履歴が保存されない](#コマンド履歴が保存されない)
  - [シェル補完が機能しない](#シェル補完が機能しない)
  - [シェル起動が遅い](#シェル起動が遅い)
- [chezmoi](#chezmoi)
  - [変更が適用されない](#変更が適用されない)
  - [ファイル競合エラー](#ファイル競合エラー)
  - [意図しない自動コミット・プッシュ](#意図しない自動コミットプッシュ)
  - [Brewfileの編集場所](#brewfileの編集場所)
- [GPG・SSH・YubiKey](#gpgsshyubikey)
  - [GPGキーの設定](#gpgキーの設定)
  - [SSH認証が機能しない](#ssh認証が機能しない)
  - [gpg-agentの再起動](#gpg-agentの再起動)
- [Tailscale / SSH](#tailscale--ssh)
  - [GUIアプリ削除後にSSHがタイムアウトする](#guiアプリ削除後にsshがタイムアウトする)
  - [MagicDNS名が解決しない（macOS）](#magicdns名が解決しないmacos)
  - [tailscale upが設定変更を拒否する](#tailscale-upが設定変更を拒否する)
  - [SSH接続のたびに再認証を求められる](#ssh接続のたびに再認証を求められる)
  - [SSH先でxterm-ghostty terminfoエラーが出る](#ssh先でxterm-ghostty-terminfoエラーが出る)
  - [QNAPでTailscale SSHが使えない](#qnapでtailscale-sshが使えない)
- [通知システム（Claude Code連携）](#通知システムclaude-code連携)
  - [通知が表示されない（macOS）](#通知が表示されないmacos)
  - [通知が表示されない（Linux）](#通知が表示されないlinux)
  - [statuslineが正しく表示されない](#statuslineが正しく表示されない)
- [ツール別の問題](#ツール別の問題)
  - [Homebrew / Linuxbrewの問題](#homebrew--linuxbrewの問題)
  - [topgradeの更新が失敗する](#topgradeの更新が失敗する)
  - [Zellijプラグインの問題](#zellijプラグインの問題)
  - [Neovimの問題](#neovimの問題)
  - [フォントが正しく表示されない](#フォントが正しく表示されない)
- [Linux固有の問題](#linux固有の問題)
  - [日本語入力（fcitx5）が機能しない](#日本語入力fcitx5が機能しない)
  - [Docker Desktopの権限問題](#docker-desktopの権限問題)
  - [SSH/VNCサービスの設定](#sshvncサービスの設定)
- [診断コマンド集](#診断コマンド集)
  - [環境確認](#環境確認)
  - [プロファイリング](#プロファイリング)
  - [chezmoi状態確認](#chezmoi状態確認)
  - [ログ確認](#ログ確認)

## 初期セットアップ

### Homebrewのインストールに失敗する

**症状**: Homebrew/Linuxbrewのインストールスクリプトがエラーで終了する

**原因と解決方法:**

**macOS:**

```bash
# Xcode Command Line Toolsがインストールされているか確認
xcode-select -p

# インストールされていない場合
xcode-select --install

# ネットワーク問題の場合は、一時的にVPNを切断
# 再度Homebrewインストールを実行
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Linux:**

```bash
# 依存パッケージのインストール
sudo apt update
sudo apt install build-essential procps curl file git

# 再度Linuxbrewインストールを実行
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### chezmoi initが途中で止まる

**症状**: `chezmoi init --apply` が途中でフリーズまたはエラーで停止する

**原因**: `run_once` スクリプトの実行時にネットワークエラーやパッケージインストール失敗が発生

**解決方法:**

```bash
# 1. chezmoiの状態を確認
chezmoi status

# 2. 詳細ログを有効にして再試行
chezmoi apply -v

# 3. 失敗したrun_onceスクリプトの状態をリセット（後述）
```

### run_onceスクリプトが失敗した場合の再実行

**症状**: `run_once_*.sh` スクリプトが失敗したが、chezmoiは「既に実行済み」として再実行しない

**原因**: chezmoiはスクリプトの実行状態を `~/.local/share/chezmoi/.state.boltdb` に記録している

**解決方法:**

```bash
# 特定のスクリプトの実行状態をリセット
chezmoi state delete-bucket --bucket=scriptState

# 再度適用
chezmoi apply -v

# または、特定のスクリプトのみ手動実行
bash ~/.local/share/chezmoi/.chezmoiscripts/run_once_before_install-packages.sh.tmpl
```

> [!WARNING]
> `delete-bucket` は **すべての** run_once スクリプトの状態をリセットします。
> 必要に応じて、スクリプトを手動で再実行してください。

### デフォルトシェルの変更

**症状**: Zshがインストールされているが、ログインシェルがBashのまま

**解決方法:**

**macOS:**

```bash
# Homebrew版Zshのパスを確認
brew --prefix zsh

# デフォルトシェルを変更
sudo chsh -s $(brew --prefix)/bin/zsh

# ログアウトして再ログイン
```

**Linux:**

```bash
# Zshのパスを確認
which zsh

# デフォルトシェルを変更
chsh -s $(which zsh)

# ログアウトして再ログイン
```

> [!NOTE]
> シェル変更後は、**必ずログアウト**してから新しいターミナルを開いてください。

## シェル・プロンプト

### コマンドが見つからない（PATH問題）

**症状**: `brew: command not found`、`starship: command not found` など

**原因**: `~/.zprofile` が読み込まれていない、またはHomebrew初期化が実行されていない

**診断:**

```bash
# PATHを確認
echo $PATH

# .zprofileが存在するか確認
ls -la ~/.zprofile

# Homebrewが初期化されているか確認（macOS）
which brew
```

**解決方法:**

```bash
# .zprofileが存在しない場合
chezmoi apply ~/.zprofile

# 手動でHomebrew初期化（一時的）
# macOS (Apple Silicon):
eval "$(/opt/homebrew/bin/brew shellenv)"

# macOS (Intel):
eval "$(/usr/local/bin/brew shellenv)"

# Linux:
eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"

# 新しいシェルで確認
exec zsh
```

### 非対話シェルだけツールのバージョンが違う（mise が効かない）

**症状**: 対話シェルでは mise が固定したバージョンが使われるのに、スクリプト・Git フック・エディタのタスク・
GUI から起動したアプリでは別のバージョン（多くは Homebrew 版）が使われる。
例: `zsh -lic 'node --version'` は v24.19.0 なのに `zsh -lc 'node --version'` は v26.7.0。

**原因**: zsh の起動ファイルの読み込み範囲が Homebrew と mise で非対称だったこと。

| 設定 | 記述場所 | 到達するシェル |
| --- | --- | --- |
| Homebrew | `~/.zprofile` の `path=(...)` と `brew shellenv`、加えて `/etc/paths.d/homebrew` | ほぼ全て |
| mise `activate` | `~/.zshrc` | 対話シェルのみ |

`mise activate zsh`（`--shims` なし）は zsh の `precmd` フックで PATH を書き換える方式なので、
`.zshrc` を読まないシェルでは一切効かず、Homebrew 側のバイナリがそのまま使われる。

**診断:**

```bash
# 3種のシェルで比較する。-lic だけ結果が違えば本件
for m in -c -lc -lic; do printf "%-4s " "$m"; zsh $m 'command -v node' ; done

# Homebrew 側に競合バイナリがあるか
which -a node
```

**解決方法:**

`~/.zprofile` が Homebrew 初期化の**後**に mise の shims を PATH へ載せる
（`chezmoi apply ~/.zprofile` で反映される）。shims は実行時にバージョンを解決する薄いラッパーなので、
フックが走らないシェルでも効く。対話シェルでは `.zshrc` の `mise activate` が実 install パスを
前に出すため、`command -v node` が shims を指さないのが正常。

```bash
# 一時的に手当てする場合
eval "$(mise activate zsh --shims)"
```

競合バイナリ自体を残さないため、node を推移的に引き込む Homebrew formula は使わない方針
（`markdownlint-cli2` は Brewfile から外し、mise の npm バックエンドへ移設済み）。
`brew uses --installed --recursive node` が空であることを保てば再発しない。

### Sheldonプラグインが読み込まれない

**症状**: シェル起動時にSheldonプラグイン（autosuggestions、syntax-highlightingなど）が機能しない

**診断:**

```bash
# Sheldonがインストールされているか
which sheldon

# プラグインロックファイルを確認
ls -la ~/.config/sheldon/plugins.lock

# Sheldonが正しく設定されているか
sheldon source
```

**解決方法:**

```bash
# プラグインを更新
sheldon lock --update

# .zshrcを再読み込み
source ~/.zshrc

# それでも解決しない場合、ロックファイルを削除して再生成
rm ~/.config/sheldon/plugins.lock
sheldon lock --update

# 新しいシェルで確認
exec zsh
```

### Starshipプロンプトが表示されない

**症状**: シェル起動後もStarshipプロンプトが表示されず、デフォルトプロンプトのまま

**診断:**

```bash
# Starshipがインストールされているか
which starship

# .zshrcでStarship初期化が記載されているか確認
grep "starship init" ~/.zshrc
```

**解決方法:**

```bash
# Starshipがインストールされていない場合
brew install starship

# .zshrcを再読み込み
source ~/.zshrc

# それでも表示されない場合、手動で初期化
eval "$(starship init zsh)"

# 新しいシェルで確認
exec zsh
```

### コマンド履歴が保存されない

**症状**: 新しいコマンドを入力しても、シェルを再起動すると履歴が消える

**原因**: `~/.zshrc` に履歴設定が含まれていない、または `HISTFILE` が正しく設定されていない

**診断:**

```bash
# HISTFILEの設定を確認
echo $HISTFILE

# .zsh_historyファイルが存在するか
ls -la ~/.zsh_history

# .zshrcの履歴設定を確認
grep "HISTFILE" ~/.zshrc
```

**解決方法:**

```bash
# chezmoiの最新版を取得して再適用
cd ~/.local/share/chezmoi
git pull
chezmoi apply

# 手動で履歴設定を確認（.zshrcに以下が含まれているべき）
# HISTFILE="${ZDOTDIR:-$HOME}/.zsh_history"
# HISTSIZE=10000
# SAVEHIST=10000
# setopt SHARE_HISTORY

# 新しいシェルで確認
exec zsh
```

### シェル補完が機能しない

**症状**: `git <Tab>` などで補完が効かない

**原因**: Sheldonプラグインが正しくロードされていない、または補完ファイルが生成されていない

**解決方法:**

```bash
# Sheldonプラグインを更新
sheldon lock --update

# 補完ディレクトリを確認
ls -la ~/.zsh_completions/

# compinit を再実行（手動）
autoload -Uz compinit && compinit

# 新しいシェルで確認
exec zsh
```

### シェル起動が遅い

**症状**: ターミナルを開くと、シェルの起動に3秒以上かかる

**原因**: プラグインの読み込み、補完の初期化、外部コマンドの実行などが影響

**診断:**

```bash
# .zshrcの先頭に以下を追加してプロファイリング
zmodload zsh/zprof

# .zshrcの末尾に以下を追加
zprof

# 新しいシェルを起動すると、処理時間が表示される
exec zsh
```

**解決方法:**

```bash
# プロファイリング結果を確認し、遅い処理を特定
# - compinit が遅い場合: キャッシュを有効化（.zshrcに既に含まれているはず）
# - Sheldon が遅い場合: プラグインを減らす
# - 外部コマンド（fastfetch等）が遅い場合: 実行条件を見直す

# プロファイリングを無効化するには、上記の追加行を削除
```

> [!NOTE]
> `.zshrc` の10-11行目にプロファイリング用のコメントアウト済みコードがあります。

## chezmoi

### 変更が適用されない

**症状**: `chezmoi edit` で変更したのに、実際のファイルに反映されない

**診断:**

```bash
# 変更内容を確認
chezmoi diff

# chezmoiの状態を確認
chezmoi status

# 管理されているファイル一覧
chezmoi managed
```

**解決方法:**

```bash
# 変更を適用
chezmoi apply

# 強制的に上書き
chezmoi apply --force

# 詳細ログを有効にして適用
chezmoi apply -v
```

### ファイル競合エラー

**症状**: `chezmoi apply` で「file has changed」と表示される

**原因**: chezmoiソースと実際のファイルが異なる（手動編集された可能性）

**解決方法:**

```bash
# 差分を確認
chezmoi diff <file>

# オプション1: chezmoiソースで上書き
chezmoi apply --force

# オプション2: 実際のファイルをchezmoiに取り込む
chezmoi add <file>

# オプション3: マージツールで解決
chezmoi merge <file>
```

### 意図しない自動コミット・プッシュ

**症状**: `chezmoi apply` のたびにGitコミット・プッシュが自動実行される

**原因**: `chezmoi.toml` で `git.autoCommit` と `git.autoPush` が有効になっている

**無効化する方法:**

```bash
# chezmoi設定ファイルを編集
chezmoi edit-config

# 以下のように変更（autoCommit/autoPushをfalseに）
[git]
    autoCommit = false
    autoPush = false
```

> [!NOTE]
> この設定を無効化すると、手動で `git add/commit/push` する必要があります。

### Brewfileの編集場所

**症状**: `~/Brewfile` を編集しても、`chezmoi diff` で変更が検出されない

**原因**: Brewfileは `~/.local/share/chezmoi/Brewfile` にのみ存在し、ホームディレクトリにはコピーされない設計

**正しい編集方法:**

```bash
# chezmoi経由で編集（推奨）
chezmoi cd
vim Brewfile

# または、直接編集
vim ~/.local/share/chezmoi/Brewfile

# パッケージをインストール
brew bundle --file=~/.local/share/chezmoi/Brewfile
```

## GPG・SSH・YubiKey

### GPGキーの設定

**症状**: シェル起動時に `gpgconf not found` エラーが表示される

**原因**: GPGがインストールされていない

**解決方法:**

```bash
# GPGのインストール確認
which gpg

# インストールされていない場合
brew install gnupg

# GPGキーのインポート
gpg --keyserver hkps://keys.openpgp.org --search-keys shin@sforzando.co.jp

# キーを信頼
gpg --edit-key KEYID
> trust
> 5 (I trust ultimately)
> quit
```

### SSH認証が機能しない

**症状**: GitHubへのSSH接続が失敗する、または `ssh-add -L` でキーが表示されない

**原因**: GPG AgentがSSH Agentとして機能していない

**診断:**

```bash
# SSH_AUTH_SOCK が設定されているか
echo $SSH_AUTH_SOCK

# gpg-agent が起動しているか
gpgconf --list-dirs agent-socket

# SSH鍵がロードされているか
ssh-add -L
```

**解決方法:**

```bash
# GPG Agentを再起動
gpgconf --kill gpg-agent
gpg-agent --daemon

# .zshrcを再読み込み
source ~/.zshrc

# SSH認証を確認
ssh -T git@github.com
```

### gpg-agentの再起動

**症状**: GPG Agentが応答しない、またはSSH認証が突然機能しなくなる

**解決方法:**

```bash
# GPG Agent を完全に停止
gpgconf --kill gpg-agent

# 再起動（.zshrcで自動起動される）
exec zsh

# 手動で起動する場合
gpg-agent --daemon --enable-ssh-support
```

## Tailscale / SSH

SSH接続はTailscale SSH（WireGuardのノードIDで認証、鍵レス）を主軸にしている。設定は
`~/.ssh/config`（`private_dot_ssh/private_config`）で管理し、`HostName` には MagicDNS名ではなく
Tailscale IP（100.x）を使う（理由は後述）。macOSは **オープンソース版 tailscaled（Homebrew formula）** を使う。

### GUIアプリ削除後にSSHがタイムアウトする

**症状**: macOSでGUI版TailscaleをアンインストールしOSS版に移行した後、`tailscale ping` は通るのに
`ssh <host>` が `Operation timed out` になる（outbound TCPだけ失敗）。

**原因**: 旧GUI版の **ネットワークSystem Extensionが残存**し、OSS版 tailscaled と二重稼働している。

**解決方法:**

```bash
# 残骸を確認
systemextensionsctl list | grep tailscale

# 残っていたら除去（再起動でorphan拡張が消えることが多い）。確実なのは再起動。
sudo reboot

# 再起動後もOSS版サービスを起動し直す
sudo brew services restart tailscale
sudo tailscale up --ssh
```

> 教訓: GUI版→OSS版へ移行する際は、.app を消す前に standalone 版アプリの正規アンインストールで
> System Extension も解除しておく。

### MagicDNS名が解決しない（macOS）

**症状**: `ssh host.taile7dbc.ts.net` が `Could not resolve hostname` になる。`nslookup host... 100.100.100.100`
では正しく解決する。

**原因**: OSS版 tailscaled on macOS は `/etc/resolver` に **search domain しか登録せず**、MagicDNS
リゾルバ（100.100.100.100）への振り分けを張らないことがある。

**解決方法**: ssh config の `HostName` を **Tailscale IP（100.x）** にする（このリポジトリはこの方式）。

```bash
# 各ホストのTailscale IPを確認
tailscale ip <host>
tailscale status
```

### tailscale upが設定変更を拒否する

**症状**: `tailscale up --ssh` 実行時に `requires mentioning all non-default flags` エラー。

**原因**: `tailscale up` は既存の非デフォルト設定をすべて再明示しないと上書きを拒否する。

**解決方法:**

```bash
# 既存の非デフォルトフラグを確認
tailscale debug prefs

# 既存フラグ（例: --accept-routes）を併記して実行
sudo tailscale up --ssh --accept-routes
# または現行設定をリセット（他の非デフォルト設定も消える点に注意）
sudo tailscale up --ssh --reset
```

### SSH接続のたびに再認証を求められる

**症状**: 自分の端末同士のSSHでも、約12時間ごとにブラウザでの再認証を求められる。

**原因**: Tailscaleのデフォルトの SSH ACL は **check モード**（定期的な再認証）。

**解決方法**: 管理コンソール → Access controls の SSHルール（`src: autogroup:member` → `dst: autogroup:self`）の
**Check mode を Off**（`action: check` → `accept`）にする。反映確認:

```bash
tailscale debug netmap | grep -i holdAndDelegate   # 消えていればaccept
```

### SSH先でxterm-ghostty terminfoエラーが出る

**症状**: SSH接続時に `tput: unknown terminal "xterm-ghostty"` が複数行出る、入力が不安定。

**原因**: GhosttyはSSH先へ `TERM=xterm-ghostty` を送るが、リモートにその terminfo が無い。

**解決方法**: Ghostty設定（`~/.config/ghostty/config`）で公式のSSH統合機能を有効化する。

```ini
# shell-integration = none のままでOK（GHOSTTY_SHELL_FEATURES経由で効く）
shell-integration-features = cursor,no-sudo,title,ssh-env,ssh-terminfo,path
```

- SSH時に `xterm-ghostty` terminfo を自動導入し、`tic` の無いホストでは `xterm-256color` にフォールバック。
- 反映には Ghostty の設定リロード（⌘⇧,）＋新規ウィンドウ、または再起動が必要
  （`echo $GHOSTTY_SHELL_FEATURES` に `ssh-env`・`ssh-terminfo` が出れば有効）。

### QNAPでTailscale SSHが使えない

**症状**: QNAP上で `tailscale up --ssh` が `The Tailscale SSH server does not run on QNAP.` で失敗。

**原因**: QNAPのTailscaleパッケージは Tailscale SSH サーバ機能を含まない。

**解決方法**: QNAPは **Tailscale経由＋標準sshd**（パスワードまたはSSH鍵）で接続する。ssh config の
`HostName` は Tailscale IP のまま、認証だけ従来方式にする。

## 通知システム（Claude Code連携）

### 通知が表示されない（macOS）

**症状**: Claude Codeのフックが実行されても、macOSの通知が表示されない

**原因**: `terminal-notifier` がインストールされていない、または `jq` が不足

**診断:**

```bash
# terminal-notifier のインストール確認
which terminal-notifier

# jq のインストール確認
which jq
```

**解決方法:**

```bash
# 不足しているパッケージをインストール
brew install terminal-notifier jq

# 通知スクリプトを手動テスト
~/.claude/scripts/notify.sh "Test" "This is a test notification"
```

### 通知が表示されない（Linux）

**症状**: Claude Codeのフックが実行されても、Linuxの通知が表示されない

**原因**: `notify-send`（libnotify）がインストールされていない、または `jq` が不足

**診断:**

```bash
# notify-send のインストール確認
which notify-send

# jq のインストール確認
which jq
```

**解決方法:**

```bash
# Debian/Ubuntu系
sudo apt install libnotify-bin jq

# Arch系
sudo pacman -S libnotify jq

# 通知スクリプトを手動テスト
~/.claude/scripts/notify.sh "Test" "This is a test notification"
```

### statuslineが正しく表示されない

**症状**: Claude Codeのstatuslineに情報が表示されない、またはエラーが出る

**原因**: `ccstatusline` が PATH で解決できない、または node ランタイム未導入

**診断:**

```bash
# ccstatusline の解決確認
command -v ccstatusline || mise which ccstatusline

# 実データを流して単体テスト
echo '{"model":{"display_name":"Opus"},"workspace":{"current_dir":"'"$PWD"'"},"context_window":{"used_percentage":42,"context_window_size":200000}}' | ccstatusline
```

**解決方法:**

```bash
# ccstatusline は mise の npm バックエンドツール（config.toml で宣言）。
# node バージョン非依存の install dir に入るため、どのリポジトリの node pin でも
# PATH に載る。再導入は config.toml 由来の一括インストールで十分。
mise install

# 個別に入れ直したい場合
mise use -g npm:ccstatusline
```

**cz-emoji が見つからない / commitizen がアダプタ読込で失敗する場合:**

cz-emoji は bin を持たないアダプタなので npm バックエンドツールにできず、node バージョン非依存の
固定 prefix `~/.local/share/cz-emoji/lib/node_modules/cz-emoji`（`~/.czrc` が絶対パスで参照）に置く。
この場所は LTS node の昇格でも移動しないため通常は壊れない。手動で削除した等で欠けたら再導入する。

```bash
chezmoi apply   # run_onchange の再実行で再導入。または手動で:
mise exec node@lts -- npm install --global --prefix "${HOME}/.local/share/cz-emoji" cz-emoji
```

## ツール別の問題

### Homebrew / Linuxbrewの問題

**症状**: `brew doctor` でエラーや警告が表示される

**一般的な解決方法:**

```bash
# Homebrewの診断
brew doctor

# Homebrewのアップデート
brew update

# 壊れたシンボリックリンクの修復
brew cleanup

# 権限の修復（macOS）
sudo chown -R $(whoami) $(brew --prefix)/*
```

### topgradeの更新が失敗する

**症状**: `topgrade` 実行時に特定のツールの更新が失敗する

**原因**: `.config/topgrade.toml` の設定で一部のツールが無効化されていない

**解決方法:**

```bash
# topgrade設定を編集
chezmoi edit ~/.config/topgrade.toml

# 失敗するツールを無効化（例: helix）
[misc]
disable = ["helix"]

# 適用
chezmoi apply
```

> [!NOTE]
> `.config/topgrade.toml` では既にhelixが無効化されています。

### Zellijプラグインの問題

**症状**: Zellijのプラグイン（zjstatus、zsm.wasm）がロードされない

**原因**: プラグインがダウンロードされていない、またはパスが正しくない

**診断:**

```bash
# プラグインファイルが存在するか確認
ls -la ~/.config/zellij/plugins/
```

**解決方法:**

```bash
# プラグインを手動でダウンロード
mkdir -p ~/.config/zellij/plugins

# zjstatus
curl -L https://github.com/dj95/zjstatus/releases/latest/download/zjstatus.wasm \
  -o ~/.config/zellij/plugins/zjstatus.wasm

# Zellijを再起動
zellij kill-all-sessions
```

> [!WARNING]
> `config.kdl` 内のプラグインパス（`/Users/suzuki/...`）がハードコードされています。
> 他のマシンでは動作しない可能性があります。

### Neovimの問題

**症状**: Neovimでプラグインがロードされない、またはエラーが表示される

**診断:**

```bash
# lazy.nvimの状態を確認
nvim
:Lazy

# プラグインの同期
:Lazy sync
```

**解決方法:**

```bash
# lazy.nvimのキャッシュをクリア
rm -rf ~/.local/share/nvim/lazy

# Neovimを再起動してプラグインを再インストール
nvim
:Lazy restore
```

### フォントが正しく表示されない

**症状**: ターミナルで絵文字やアイコンが文字化けする

**原因**: Nerd Fontがインストールされていない

**解決方法:**

**macOS:**

```bash
# Brewfileに既に含まれているはず
brew install font-hackgen-nerd font-mononoki-nerd-font

# ターミナル（Ghostty等）でフォントを設定
# ~/.config/ghostty/config で font-family を確認
```

**Linux:**

```bash
# フォントをダウンロード
mkdir -p ~/.local/share/fonts
cd ~/.local/share/fonts

# HackGen Nerd Font をダウンロード（例）
wget https://github.com/ryanoasis/nerd-fonts/releases/download/v3.0.2/HackGen.zip
unzip HackGen.zip
rm HackGen.zip

# フォントキャッシュを更新
fc-cache -fv
```

## Linux固有の問題

### 日本語入力（fcitx5）が機能しない

**症状**: Linux環境で日本語入力ができない

**原因**: fcitx5がインストールされていない、または環境変数が設定されていない

**解決方法:**

```bash
# fcitx5を手動でインストール（run_once_install-fcitx5.shが失敗した場合）
bash ~/.local/share/chezmoi/.chezmoiscripts/run_once_install-fcitx5.sh.tmpl

# または手動でインストール
sudo apt install fcitx5 fcitx5-mozc

# 環境変数を設定（.zprofileに既に含まれているはず）
echo $GTK_IM_MODULE
echo $QT_IM_MODULE
echo $XMODIFIERS

# fcitx5を起動
fcitx5 &
```

### Docker Desktopの権限問題

**症状**: `docker` コマンド実行時に権限エラーが表示される

**原因**: ユーザーが `docker` グループに追加されていない

**解決方法:**

```bash
# dockerグループに追加
sudo usermod -aG docker $USER

# ログアウトして再ログイン
# または、グループを一時的に適用
newgrp docker

# 確認
docker ps
```

### SSH/VNCサービスの設定

**症状**: Linux環境でSSH/VNCサービスが起動していない

**原因**: `run_once_after_setup-linux-services.sh` が正しく実行されていない

**解決方法:**

```bash
# スクリプトを手動実行
bash ~/.local/share/chezmoi/.chezmoiscripts/run_once_after_setup-linux-services.sh.tmpl

# サービスの状態を確認
sudo systemctl status ssh
sudo systemctl status x11vnc

# サービスを手動で起動
sudo systemctl enable ssh
sudo systemctl start ssh
```

## 診断コマンド集

### 環境確認

```bash
# chezmoi の診断
chezmoi doctor

# Homebrewの診断
brew doctor

# Sheldonの状態確認
sheldon source

# PATH確認
echo $PATH
which brew
which zsh
which starship
```

### プロファイリング

```bash
# Zsh起動時間の測定
time zsh -i -c exit

# Zshプロファイリング（.zshrcの10-11行目をアンコメント）
# zmodload zsh/zprof
# ...
# zprof

# 新しいシェルを起動すると、処理時間が表示される
exec zsh
```

### chezmoi状態確認

```bash
# 管理されているファイル一覧
chezmoi managed

# 管理されていないファイル一覧
chezmoi unmanaged

# 変更があるファイル
chezmoi status

# 詳細ログ付きで適用
chezmoi apply -v
```

### ログ確認

```bash
# システムログ（macOS）
log show --predicate 'process == "zsh"' --last 10m

# システムログ（Linux）
journalctl -u ssh --since "10 minutes ago"

# Claude Codeのフック実行ログ
# （標準出力に表示される）
```

**関連ドキュメント:**

- [README.md](./README.md) - 初期セットアップガイド
- [MIGRATION.md](./MIGRATION.md) - Preztoからの移行ガイド
