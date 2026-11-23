---
name: issue-defaults
description: Use when creating a GitHub Issue — applies the maintainer's personal defaults for title type, assignee, Priority field, and Milestone. Triggers on "issueを起票", "create an issue", "file an issue", "open a ticket" in any repository.
---

# GitHub Issue Defaults

Apply all rules unless the user explicitly overrides a value.

For the Pull Request side, see `pr-defaults`.

## 1. Title type & label

Decision rule (maintainer-confirmed): **a bug → `fix`; anything that is not a bug → `feat`.**

Format the title like a cz-emoji commit subject, with the emoji as a Unicode character:

```plain
<type>: <emoji> <subject>
```

| type  | title prefix |
| ----- | ------------ |
| feat  | `feat: ✨`   |
| fix   | `fix: 🐛`    |

- Why: titles are read in places that do not expand `:shortcode:` (CLI output, notifications, branch pickers), so a literal emoji renders everywhere
- Subject in English, starting with a lowercase letter, no scope — the same rules as the commit subject
- If the user explicitly asks for another type from `~/.czrc` (e.g. `docs`, `chore`), use that type's emoji from the same table
- Example: `gh issue create --title "feat: ✨ fold GenCo concepts into the architecture docs" ...`

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
