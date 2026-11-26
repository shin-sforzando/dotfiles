---
name: wtp-worktrees
description: Use when creating, entering, or cleaning up a git worktree in a repository whose root has a .wtp.yml or an orca.yaml — starting isolated feature work, branching off for a parallel task, or removing a finished worktree. Chooses between Orca (when this session runs inside Orca) and wtp (Worktree Plus), and covers the mandatory session move into the new worktree.
---

# wtp / Orca Worktrees

## Applies when

The repository root contains a `.wtp.yml` (set up for [wtp](https://github.com/satococoa/wtp), Worktree Plus) or an `orca.yaml` (set up for [Orca](https://orca.dev/docs)).

Neither file → this skill does not apply; fall back to `superpowers:using-git-worktrees`.

## Rule 0 — pick the tool: Orca inside Orca, wtp otherwise

```bash
[ -n "${ORCA_APP_VERSION-}" ] && [ -f orca.yaml ] && echo orca || echo wtp
```

- **Orca** when this session runs inside Orca (Orca sets `ORCA_APP_VERSION`, `ORCA_CLI_COMMAND` and friends in its chats and terminals) **and** the repo has an `orca.yaml`. The worktree then shows up in Orca's sidebar with its setup tab, linked issue and PR view.
- **wtp** in every other case: outside Orca, or a repo with only `.wtp.yml` — Orca would create the worktree without running any setup.

Both tools only work if the repo's config runs a setup. A repo that carries both files ideally points them at one shared setup script, so the resulting worktree is identical either way; if the two configs diverge, read both before choosing.

## Rule 1 — never `git worktree add`

The repo's setup (`.wtp.yml` `post_create` / `orca.yaml` `scripts.setup`) makes a new worktree usable: copying gitignored files the dev environment needs (`.env`, git-secret plaintexts), symlinking shared directories, approving `direnv`, installing dependencies.
Raw `git worktree add` skips all of it and leaves a broken environment that fails in confusing ways later.

This skill overrides `superpowers:using-git-worktrees`' git fallback in any repository that has either file.
The setup differs per repository — **read the repo's own config** rather than assuming what setup happened.

### Creating with Orca

```bash
orca worktree create --repo path:"$(git rev-parse --show-toplevel)" \
  --name <branch> --branch <branch> \
  --base-branch origin/main --issue <N> \
  --setup run --no-parent --json
```

- `--branch` pins the Git branch name to the repo's convention; without it Orca derives one (and may add a configured prefix).
- `--base-branch origin/main`: Orca reads `scripts.setup` from the branch the worktree starts from, so the base must contain `orca.yaml`.
- `--setup run` forces the setup instead of inheriting a per-user policy.
- `--no-parent` keeps Orca from recording the current worktree as a parent of unrelated work.
- Do **not** pass `--agent`: that starts a second agent inside Orca instead of continuing in this session.
- The JSON result's `worktree.path` is the path for Rule 2.

### Creating with wtp

`wtp add -b <branch> [<commit>]` prints the new worktree's absolute path (`--quiet` prints only the path).
wtp reads `.wtp.yml` from the **main checkout**, not from the branch: pull main first, or a changed `.wtp.yml` is ignored.

## Rule 2 — move the session into the new worktree, before any other tool call

This is the step that is easiest to skip and most expensive to skip.

Immediately call:

```text
EnterWorktree(path: "<the new worktree's absolute path>")
```

Then verify with `pwd`. This works for Orca worktrees too: they are ordinary git worktrees under Orca's workspace folder.

A Bash `cd` is **not** a substitute. It moves only the Bash tool's directory; `Read`, `Edit`, `Write`, `Glob` and `Grep` still resolve against the *session* working directory.
The result is an agent that believes it is on the feature branch while silently editing the main checkout — and an endless series of unexplained path problems.

`wtp cd` does not help either. It only *prints* a path; the actual `cd` comes from a shell function installed in a human's interactive shell, which an agent does not have.

Neither tool's setup can perform the move for you: it runs in a subprocess and can never change the caller's working directory.

When the work is done, leave with `ExitWorktree(action: "keep")`. `remove` would delete a worktree that wtp or Orca is managing.

## Rule 3 — a successful create does not mean the setup succeeded

**wtp** (verified against wtp v2.10.3):

- wtp aborts the whole hook chain at the first hook that exits non-zero. Every later hook is skipped.
- `wtp add` still exits 0 in that case, and still reports `✅ Worktree created successfully!`.

So read the output for `Warning: Hook execution failed` rather than trusting the exit code.

**Orca** (verified against Orca 1.4.272):

- `orca worktree create` returns as soon as the worktree exists. The setup then runs in a separate terminal tab titled "セットアップ" (Setup) and takes minutes (dependency installs).
- Find that tab with `orca terminal list --worktree path:<path> --json` and poll `orca terminal read --terminal <handle>` until the shell prompt is back. `orca terminal wait --for tui-idle` times out on a plain shell; do not rely on it.

Either way, confirm that what the repo's setup was supposed to produce actually exists (typically copied `.env` files, symlinks, `node_modules`, a Python `.venv`) before working in the worktree.

A corollary for anyone editing a setup: put the steps that must never be skipped **first**, and never insert a step that can fail ahead of them.

## Quick reference

| Goal | wtp | Orca |
| --- | --- | --- |
| New branch + worktree | `wtp add -b <branch> [<commit>]` | `orca worktree create --name <b> --branch <b> --base-branch origin/main --setup run --no-parent --json` |
| Worktree from an existing branch | `wtp add <branch>` | — (use wtp) |
| Run a command in a worktree without moving | `wtp exec <name> -- <command>` | `orca terminal create --worktree path:<path> --command "<cmd>"` |
| List worktrees | `wtp list` | `orca worktree list --json` |
| Link a PR / issue | — | `orca worktree set --worktree path:<path> --pr <N>` / `--issue <N>` |
| Remove a worktree | `wtp remove <name>` | `orca worktree rm --worktree path:<path>` |
| Remove worktree + its branch | `wtp remove --with-branch <name>` | `orca worktree rm` deletes a fully merged branch; it keeps an unmerged one |

Run `wtp <command> --help` / `orca worktree <command> --help` for full options.

Branch names follow the target repository's own convention. A common one is `{issue number}_feature_name` (e.g. `123_add_login_form`); check whether the repo zero-pads the number before assuming either form.

## Cleanup

Remove a worktree with the tool that created it: `wtp remove` for wtp worktrees (under `../worktrees/`), `orca worktree rm` for Orca worktrees (under Orca's workspace folder, default `~/orca/workspaces/<repo>/`). Orca cleans its own records up on its next refresh if a worktree disappears some other way.

If a branch delete is refused as "not fully merged" right after a merge, the local main is just behind: check `git merge-base --is-ancestor <branch> origin/main` and only then `git branch -D`.

For post-merge bulk cleanup, `/commit-commands:clean_gone` (after `git fetch --prune`) removes worktrees and local branches for every `[gone]` branch while leaving active worktrees untouched.

## Red flags — STOP

- About to run `git worktree add` in a repo that has `.wtp.yml` or `orca.yaml` → use Rule 0's tool instead.
- Inside Orca, the repo has `orca.yaml`, and you are about to run `wtp add` → use `orca worktree create`.
- About to pass `--agent` to `orca worktree create` → don't; this session does the work.
- The worktree was just created and you are about to read or edit a file → STOP. `EnterWorktree` first, every time, no exceptions.
- Orca setup still running (its terminal has not returned to a prompt) → wait; the dependencies are not there yet.
- You think a Bash `cd` or `wtp cd` moved you → it did not. Run `pwd` and check.
- `wtp add` printed `Warning: Hook execution failed` and you moved on → every later hook was skipped; fix the worktree before working in it.
