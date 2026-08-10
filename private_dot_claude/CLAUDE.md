# CLAUDE.md - User Scope Guidelines

## Guidelines

- Respond in Japanese by default, but match the user's language when they write in another language.
- All comments and log output in source code must be in English - Explain `Why/Why Not`, not `What` or `How`
- Do not ignore Linter warnings
- Delegate read-only, multi-file investigation (codebase search, spec reading, log scans, web research) to the `recon` subagent
  - MANDATORY when it would use 5+ read calls or read 3+ files.
- Git operation rules - Git operations are basically performed by the user
  - Working directly on the main branch is strictly prohibited

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
