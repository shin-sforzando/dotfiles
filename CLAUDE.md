# CLAUDE.md - dotfiles (chezmoi source)

## Git

- Commit and push directly to `main`. Do not create branches, worktrees, or PRs here.
  This overrides the user-scope "never work on main" rule and the `/cppr`,
  `pr-defaults`, and `wtp-worktrees` flows
  - Why: `chezmoi apply` deploys whatever the source checkout currently has. When the
    checkout is left on a feature branch, apply silently deploys that branch (or misses
    changes merged to `main`), which has caused real accidents
- Leave the checkout on `main` when finishing work
- Never run write work in parallel here (agents or sessions); parallelize read-only investigation only
  - Why: everyone shares one `main` checkout with no worktree isolation, and chezmoi's
    autoCommit/autoPush plus Zed/snapzy runtime rewrites add side effects outside the prompt,
    so concurrent writers race even when their tasks look independent
