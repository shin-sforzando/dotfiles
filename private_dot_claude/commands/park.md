Save the current work context to NOTES.md so you can resume easily later.

Steps:
1. Read NOTES.md if it exists (at the project root)
2. Run `git log --oneline -10` to review recent commits
3. Run `git status` and `git diff --stat HEAD` to see current changes
4. Scan for TODO/FIXME comments in recently modified files
5. Update NOTES.md with the following structure (replace existing content):

```
## 最後にやったこと（YYYY-MM-DD）
- [Bullet points summarizing what was done, inferred from git log and diffs]

## 次にやること
- [Ask the user what they plan to do next, or infer from open TODOs and issues]

## 積み残し・考え中
- [Preserve existing items from previous NOTES.md; add new blockers or pending decisions]
```

6. Show the user the updated NOTES.md content
7. Do NOT commit or push — just update the file

Keep each section concise. This is a handoff note for your future self.
