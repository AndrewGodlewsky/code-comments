## Review of feat-01 (junior-v3, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a row_count definition and a staleness note to Terms and Step 3, plus a Step 4 guard that falls through to Step 5 if more than 10,000 rows are read.
- Step 4: made explicit that the download starts only after the full body arrives with no progress indicator, and that the deadline is checked after each page.
- Terms: clarified enqueue, workers, ctx contents and that queue job states are not used by the plan.
- Step 6: said where user and clients come from, and that a permission-removed job sends no email.
- Step 8: the done update now applies only WHERE status='running', so a late old job cannot overwrite a failed row or send an email; Step 5 stale-row note points to this.
- Step 9: stated it is the same handler run and that a failure consumes one of the 3 attempts.
- Step 11: status block placement, button disabled while queued or running, and the message when a click returns the existing export.
- Test 1: added a stale-low row_count case.
- Reordered into the newcomer layout: summary, terms, new table, state table, numbered steps, tests, open questions.
- Merged the separate 'New state' section into Terms, and moved the States table before the steps.
- Cut the 'How each requirement is met' section, which repeated the steps.
- Moved the stuck-row (3 hour) sweep into the start of Step 5 as an explicit action, folding the standalone note into the failure list.
- Merged the two overlapping 'no half-written file' and abort notes in Step 7, and dropped the separate memory/time paragraphs into shorter lines.
- Trimmed Step 4 detail (removed browser progress-indicator commentary and the redundant memory justification) and removed duplicate restatements of the Rows API rules.
- Shortened Step 6, 9, 10 and 11 failure notes and removed repeated explanations of why choices were made.
- Removed references to 'Step 11' and 'see below' style pointers where a step can state it itself; kept only the open-question numbers.
- Reworded open question 2 and 4 to ask the owner directly; no change in intent.

### Holes
- None.
