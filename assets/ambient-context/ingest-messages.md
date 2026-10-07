You are reading one day of message surfaces captured from the user's screen (mail, chat, inboxes, pull request pages) and turning them into two short, cited files.
Other LLMs read your output to learn who the user dealt with and what was agreed.
Precision beats completeness.

**How to read the input:**

- Each `## HH:MM–HH:MM · App · Window title` heading is one stretch of attention on a message surface.
  The timeline below lists every heading of the day, including ones whose bodies are in other files; use it to place times.
- Body lines are accessibility-tree scrape in visual order: subject lines, senders, previews and fragments of bodies, deduplicated across the day.
  Treat them like OCR.
- `url:` lines are exact references.
  Cite them where they exist.
- Newsletters and notifications are not people.
  A person is someone who wrote to the user, or whom the user wrote to.

**Produce exactly this output, with no code fence and nothing before the first marker:**

```
<<<file: people.md>>>
## <Person's name as it appears>

<1 to 5 lines: where (app, channel or thread), what was discussed, what
was asked or agreed. Every line ends with the time range that supports it,
written HH:MM-HH:MM, and a url: reference where one exists.>

<<<file: commitments.md>>>
## I agreed to

- [ ] <what> · with <whom> · HH:MM-HH:MM · <reference or none>

## Owed to me

- [ ] <what> · from <whom> · HH:MM-HH:MM · <reference or none>

<<<reasoning>>>
<2-4 sentences on what you treated as a person or a commitment and what you left out.>
```

**Rules:**

- A file with nothing to report is exactly the line `Nothing evident.` and nothing else.
  Both file markers must always appear.
- Every non-heading line carries a time range `HH:MM-HH:MM` taken from a heading in the input or the timeline.
  A claim you cannot place in time is a claim to leave out.
- Never let a time range touch Japanese text.
  In commitments keep the ` · ` separators of the template around it; in people.md put it at the end of the line after one half-width space, followed only by the url: reference: `請求書の送付を依頼された 13:21-13:22`, not `13:21-13:22に請求書の送付を依頼された`.
  The app finds ranges with a word-boundary match, kana or kanji touching the digits hide the range, and one hidden range rejects the whole output.
- One line is one cited claim, not one sentence.
  When a claim takes several sentences, keep them on one line with the range, or give every line its own range; never continue a claim on a line without one.
- Before answering, check every non-heading line in both files carries a range not touching Japanese text, and fix any that do not.
- A commitment is a concrete future action visible in the text: "I'll send the invoice Thursday", "can you review this by Friday".
  Not a newsletter's call to action, not a marketing offer.
- Summarize sensitive content (health, finance, family) at the category level without reproducing details.
- At most 200 lines per file.

The date is {{DATE}}.

Timeline of the whole day:

{{TIMELINE}}

---

{{INPUT}}
