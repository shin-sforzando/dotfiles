---
name: wtp-worktrees
description: Use when creating, entering, or cleaning up a git worktree in a repository whose root has a .wtp.yml — starting isolated feature work, branching off for a parallel task, or removing a finished worktree. Covers wtp (Worktree Plus) and the mandatory session move into the new worktree.
---

# wtp Worktrees

## Applies when

The repository root contains a `.wtp.yml`. That file is the marker that the repo is set up for [wtp](https://github.com/satococoa/wtp) (Worktree Plus).

No `.wtp.yml` → this skill does not apply; fall back to `superpowers:using-git-worktrees`.

## Rule 1 — create worktrees with `wtp add`, never `git worktree add`

`.wtp.yml` defines `post_create` hooks that make a new worktree actually usable: copying gitignored files the dev environment needs (`.env`, git-secret plaintexts), symlinking shared directories, approving `direnv`, installing dependencies.
Raw `git worktree add` skips every one of them and leaves a broken environment that fails in confusing ways later.

`wtp` is the "native worktree tool" that `superpowers:using-git-worktrees` Step 1a says to prefer.
This skill overrides that skill's git fallback in any repository that has a `.wtp.yml`.

The hooks differ per repository — **read the repo's own `.wtp.yml`** rather than assuming what setup happened.

## Rule 2 — move the session into the new worktree, before any other tool call

This is the step that is easiest to skip and most expensive to skip.

`wtp add` prints the new worktree's absolute path. Immediately call:

```text
EnterWorktree(path: "<that absolute path>")
```

Then verify with `pwd`.

A Bash `cd` is **not** a substitute. It moves only the Bash tool's directory; `Read`, `Edit`, `Write`, `Glob` and `Grep` still resolve against the *session* working directory.
The result is an agent that believes it is on the feature branch while silently editing the main checkout — and an endless series of unexplained path problems.

`wtp cd` does not help either. It only *prints* a path; the actual `cd` comes from a shell function installed in a human's interactive shell, which an agent does not have.

`.wtp.yml` cannot perform the move for you: `post_create` hooks run in a subprocess and can never change the caller's working directory. A repo may print the instruction from a hook, but carrying it out is your job.

When the work is done, leave with `ExitWorktree(action: "keep")`. `remove` would delete a worktree that `wtp` is managing.

## Rule 3 — a green `wtp add` does not mean the setup succeeded

Two failure modes to check for, verified against wtp v2.10.3:

- **wtp aborts the whole hook chain at the first hook that exits non-zero.** Every later hook is skipped. A repo whose `.wtp.yml` runs `direnv allow` before some other hook will silently skip that other hook the moment `.envrc` is missing.
- **`wtp add` still exits 0** in that case, and still reports `✅ Worktree created successfully!`.

So read the output for `Warning: Hook execution failed` rather than trusting the exit code, and confirm what the repo's hooks were supposed to produce actually exists.

A corollary for anyone editing a `.wtp.yml`: put the hooks that must never be skipped **first**, and never insert a hook that can fail ahead of them.

## Quick reference

| Goal | Command |
| --- | --- |
| Worktree from an existing branch | `wtp add <branch>` |
| New branch + worktree | `wtp add -b <branch> [<commit>]` |
| Create and run a command after hooks | `wtp add -b <branch> --exec "<command>"` |
| Print only the created path | `wtp add -b <branch> --quiet` |
| Run a command in a worktree without moving | `wtp exec <name> -- <command>` |
| List worktrees | `wtp list` (`wtp ls`) |
| Print a worktree's path | `wtp cd [<name>]` — prints only; see Rule 2 |
| Remove a worktree | `wtp remove <name>` |
| Remove a dirty worktree | `wtp remove -f <name>` |
| Remove worktree + its branch | `wtp remove --with-branch <name>` |

Run `wtp <command> --help` for full options.

Branch names follow the target repository's own convention. A common one is `NNN_feature_name` with a zero-padded 3-digit issue number, e.g. `wtp add -b 019_prepare_github_actions`.

## Cleanup

When the branch is merged, remove its worktree with `wtp remove <name>` (add `--with-branch` to also delete the branch).
Pairs with `superpowers:finishing-a-development-branch`.

For post-merge bulk cleanup, `/commit-commands:clean_gone` (after `git fetch --prune`) removes worktrees and local branches for every `[gone]` branch while leaving active worktrees untouched.
Worktree *removal* does not depend on `.wtp.yml` hooks, so going through git here is safe.

## Red flags — STOP

- About to run `git worktree add` in a repo that has `.wtp.yml` → use `wtp add` instead.
- `wtp add` succeeded and you are about to read or edit a file → STOP. `EnterWorktree` first, every time, no exceptions.
- You think a Bash `cd` or `wtp cd` moved you → it did not. Run `pwd` and check.
- `wtp add` printed `Warning: Hook execution failed` and you moved on → every later hook was skipped; fix the worktree before working in it.
- Adding a `post_create` hook above one that must always run → don't. Anything that can fail there silences everything below it.
