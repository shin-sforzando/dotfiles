# CLAUDE.md - dotfiles (chezmoi source)

## Git

- Commit and push directly to `main`. Do not create branches, worktrees, or PRs here.
  This overrides the user-scope "never work on main" rule and the `/cppr`,
  `pr-defaults`, and `wtp-worktrees` flows
  - Why: `chezmoi apply` deploys whatever the source checkout currently has. When the
    checkout is left on a feature branch, apply silently deploys that branch (or misses
    changes merged to `main`), which has caused real accidents
- Leave the checkout on `main` when finishing work
