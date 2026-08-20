---
name: issue-defaults
description: Use when creating a GitHub Issue — applies the maintainer's personal defaults for title type, assignee, Priority field, and Milestone. Triggers on "issueを起票", "create an issue", "file an issue", "open a ticket" in any repository.
---

# GitHub Issue Defaults

Apply all rules unless the user explicitly overrides a value.

For the Pull Request side, see `pr-defaults`.

## 1. Title type & label

Decision rule (maintainer-confirmed): **a bug → `fix`; anything that is not a bug → `feat`.**

## 2. Assignee → self

If no assignee was specified, self-assign:

```bash
gh issue create ... --assignee @me
```

## 3. Priority field → Medium

`Priority` is GitHub's native **Issue Field** (not a Projects v2 field), and `gh issue create/edit` has **no flag** for it.
Set it right after creating the issue with a GraphQL mutation.

Priority is Issue-only: a PR never carries it, so do not try to inherit it.

## 4. Milestone → judgment-based

No fixed default.
Pick the most fitting open milestone from the issue's content (target version / scope).

Set with `gh issue create ... --milestone "<title>"` (or `gh issue edit <N> --milestone "<title>"`).
