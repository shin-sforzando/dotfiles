# ambient-daily glossary

ambient-daily reads this file twice: the whole text goes into the prompt, and
the lists below are applied to the generated note as well, so a spelling here
holds even when the model ignores it.

## Guidance

- 敬称は「さん」を使い、「氏」は使わない。
- 社名は「Sforzando」と書く。リポジトリ名・組織名・バンドル ID（`sforzando/flipples-jp`、`jp.co.sforzando`）は小文字のまま。
- 打ち合わせは「打ち合わせ」と書く。「会議」「ミーティング」は文脈に合うときだけ使う。
- クラウドは「GCP」と書く。
- 長音は付ける（サーバー、モニター、ユーザー）。

## Replace

Each line is `variant` → `canonical`. Latin words match only as whole words,
so paths and repository names (`sforzando/flipples-jp`) are left alone.

- `Mtg` → `打ち合わせ`
- `mtg` → `打ち合わせ`
- `打合せ` → `打ち合わせ`
- `見積り` → `見積もり`
- `サーバ` → `サーバー`
- `モニタ` → `モニター`
- `sforzando` → `Sforzando`
- `topgrade` → `Topgrade`
- `Chezmoi` → `chezmoi`
- `VSCode` → `VS Code`
- `Three.js` → `three.js`
- `Arduino Uno Q` → `Arduino UNO Q`
- `VOICE` → `Voice`
- `macos` → `macOS`
- `MacOS` → `macOS`
- `Github` → `GitHub`
- `github` → `GitHub`
- `obsidian` → `Obsidian`

## Tag synonyms

Each line is `tag` → `tag to use instead`.

## Redundant tags

Each line is `tag` with `tag`: the first is dropped when both are present.

- `git` with `github`

## No link

Vault note titles that are ordinary words and are never linked automatically.

- `List`
- `Map`
- `Rating`
- `Recovering`
- `Reflection`
- `Tips`
- `Jargon`
- `寸法`
- `工法`
- `素材`
