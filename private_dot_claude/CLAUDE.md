# CLAUDE.md - User Scope Guidelines

## Guidelines

- Respond in Japanese by default, but match the user's language when they write in another language.
- All comments and log output in source code must be in English - Explain `Why/Why Not`, not `What` or `How`
- Do not ignore Linter warnings
- Delegate read-only, multi-file investigation (codebase search, spec reading, log scans, web research) to the `recon` subagent
  - MANDATORY when it would use 5+ read calls or read 3+ files.
- Git operation rules - Git operations are basically performed by the user
  - Working directly on the main branch is strictly prohibited

## Diagrams

Diagrams are authored with the `drawio` plugin skill plus the `drawio` MCP server.
The skill covers general draw.io XML rules; the points below are the local conventions
it cannot know about.

- Treat `.drawio` as a committed source artifact, not a throwaway. Default output
  directory is `docs/diagrams/`
- For any diagram needing domain-specific icons (GCP, Cisco / rack-mounted network
  gear, Kubernetes, AWS, Azure), call `mcp__drawio__search_shapes` first and paste the
  returned `style` verbatim into the `mxCell`. Substituting labelled rectangles for
  real stencils is not acceptable - the icons are the reason we use draw.io at all
- Update an existing `.drawio` through `get_page` / `set_page` rather than rewriting
  the whole file, so the other pages and their layout survive
- Diagram labels follow the language rule above (Japanese by default)
- Set `fontFamily=Hiragino Sans` on every cell that carries text. It is the only
  locally installed family that covers Latin and Japanese with one consistent face;
  leaving the font unset splits the two scripts across different fallbacks
- Never pull a web font in via `fontSource`. The desktop CLI cannot fetch it during
  export and silently falls back to a serif face - `Noto Sans JP` and `GenShinGothic`
  both resolve to zero faces on this machine and render as serif
- Do not run the CLI's `--layout` (ELK) pass on a diagram built from vendor icons.
  ELK resizes every node to fit its label, so an `aspect=fixed` stencil labelled from
  below gets stretched (a 48px Cloud SQL icon came back 192px wide). Place those nodes
  by hand on one shared centre axis and confirm the centres match before exporting.
  ELK stays useful for plain box-and-arrow diagrams whose labels sit inside the node
- Render your own work before reporting it done:
  `drawio -x -f png -e -b 10 -s 2 -o /tmp/check.png <file>.drawio`, then read the PNG.
  Misaligned connectors, wrapped labels and font fallbacks are only visible this way

## Shell

- The Bash tool keeps its working directory across calls. Do not re-anchor with `cd` on
  every command - use absolute paths or `git -C <repo>`
- Working with a worktree, never chain `cd` per command:
  - `wtp add -b <branch> --quiet` prints only the created path - capture it once
  - `wtp exec <worktree> -- <command>` runs a command in a worktree without moving
  - `wtp add -b <branch> --exec "<command>"` does both in one step
- Never wait with a foreground `sleep`. Use `run_in_background`, the Monitor tool,
  or a blocking watcher such as `gh run watch`
- Read a file with the Read tool before Edit or Write. Reading it through
  `ctx_execute_file` does not satisfy that precondition

### Git Commit Message

Git commit messages must comply with the conventions in the `~/.czrc` (cz-emoji) file below.

#### Format

```plain
<type>: <:emoji-code:> <subject>
```

- The subject must be 72 characters or fewer
- Do not include a scope
- Write emojis using text codes (e.g., `:sparkles:`); they will be converted to emojis on GitHub

| type     | code                  | 用途               |
| -------- | --------------------- | ------------------ |
| feat     | `feat: :sparkles:`    | Feature (実装)     |
| fix      | `fix: :bug:`          | Fix (修復)         |
| wip      | `wip: :construction:` | WIP (工事)         |
| chore    | `chore: :paperclip:`  | Chore (雑務)       |
| style    | `style: :art:`        | Style (美観)       |
| docs     | `docs: :notebook:`    | Documents (文書)   |
| perf     | `perf: :zap:`         | Performance (改善) |
| refactor | `refactor: :bulb:`    | Refactoring (改築) |
| test     | `test: :100:`         | Test (試験)        |
| release  | `release: :tada:`     | Release (公開)     |
