---
name: pr-defaults
description: Use when opening a GitHub Pull Request — routes to the /cppr command and applies the maintainer's rule that a PR inherits its source issue's assignee, labels, and milestone. Triggers on "PRを作成", "open a PR", "create a pull request", "PRを出して" in any repository.
---

# GitHub Pull Request Defaults

For the Issue side, see `issue-defaults`.

## 1. Use `/cppr` for the normal flow

`/cppr` does branch → commit → push → PR in one pass and already applies every rule below.
It is the personal replacement for `/commit-commands:commit-push-pr`.

Do not hand-roll `gh pr create` for the normal flow. Reach for the raw commands only when
fixing up an existing PR, or when the situation genuinely falls outside what `/cppr` covers.

## 2. Inherit from the source issue

The PR carries over the source issue's **assignee, labels, and milestone**.

Determine the source issue number from the branch name (`NNN_...`), otherwise infer it from
the change and its context. Then read what to inherit:

```bash
gh issue view <N> --json assignees,labels,milestone
```

`Priority` is **not** inherited: it is a GitHub Issue Field with no Pull Request equivalent
(see `issue-defaults`).

If the source issue has no milestone, omit `--milestone` rather than inventing one.

## 3. Close the issue from the PR body

Include a closing keyword for the source issue in the body (e.g. `To close #<N>`).
Some repositories specify the exact wording in `CONTRIBUTING.md` — follow that when present.

## 4. Fix up anything that did not apply at create time

`gh pr create` can silently drop a value it cannot resolve (an unknown label, a milestone
title that does not match). Verify the created PR and repair it with:

```bash
gh pr edit <PR> --add-assignee ... --add-label ... --milestone "..."
```
