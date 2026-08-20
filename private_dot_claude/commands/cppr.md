---
allowed-tools: Bash(git switch:*), Bash(git checkout:*), Bash(git branch:*), Bash(git add:*), Bash(git status:*), Bash(git push:*), Bash(git commit:*), Bash(git -C:*), Bash(gh pr create:*), Bash(gh pr edit:*), Bash(gh issue view:*)
description: Commit, push, and open a PR that inherits the source issue's assignee/labels/milestone
---

# cppr — commit, push, open a PR

## Context

- Current git status (cwd): !`git status`
- Current git diff (cwd, staged and unstaged changes): !`git diff HEAD`
- Current branch (cwd): !`git branch --show-current`

> ⚠️ The snapshot above runs in the **current working directory**. When work happens in a
> git worktree (an isolated branch checked out elsewhere, e.g. `../worktrees/<branch>`),
> the cwd can be a *different* branch carrying unrelated changes. Treat the snapshot as
> unverified until step 0 confirms the target checkout.

## Your task

This is the personal replacement for `/commit-commands:commit-push-pr`:
same commit/push/PR flow, plus it applies the maintainer's PR rule — the PR inherits the
**source issue's assignee, labels, and milestone** (Priority is Issue-only and not inherited).

Based on the above changes:

1. **Confirm the target checkout before any git operation.** If `$ARGUMENTS` names a
   worktree path or branch, that is the target. Compare it with `Current branch (cwd)`:
   - If they differ — or the diff shows changes you did not make — the snapshot is from
     the wrong checkout. Re-read the real changeset with `git -C <target> status` and
     `git -C <target> diff HEAD`, and run every git step below against that worktree
     (`git -C <target> ...`). Never commit from the cwd in this case.
   - Always stage files explicitly by path (`git add <paths>` / `git -C <target> add
     <paths>`), never `git add -A`/`git add .`, so another branch's changes in the same
     checkout cannot leak into the commit.

2. If on the default branch, create a new branch.
   Follow the repository's own naming convention; a common one is
   `NNN_feature_name` with a zero-padded 3-digit issue number, e.g.
   `019_prepare_github_actions`.
3. Create a single commit with an appropriate cz-emoji message
   (e.g. `feat: :sparkles: ...`, `fix: :bug: ...`).
4. Push the branch to origin.
5. Determine the **source issue number**: from the branch name (`NNN_...`), otherwise infer
   it from the change/context.
6. Read the source issue's metadata to inherit:

   ```bash
   gh issue view <N> --json assignees,labels,milestone
   ```

7. Create the PR, carrying those values over and closing the issue:

   ```bash
   gh pr create --assignee <logins> --label <labels> --milestone "<title>" \
     --body "... To close #<N> ..."
   ```

   - Include a closing keyword for the source issue in the body (e.g. `To close #<N>`).
   - If the source issue has **no** milestone, omit `--milestone`.
   - If any value could not be applied at create time, fix it up with
     `gh pr edit <PR> --add-assignee ... --add-label ... --milestone "..."`.

Do all of the above in as few messages as possible. Do not do unrelated work.
