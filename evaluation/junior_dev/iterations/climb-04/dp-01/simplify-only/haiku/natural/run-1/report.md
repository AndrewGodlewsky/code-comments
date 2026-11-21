## Review of dp-01 (simplify-only, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Removed the 'Decisions in brief' section. Its points now sit in the summary and the steps, so nothing is said twice.
- Cut the merge SQL block. The rule is stated in words in step 7, and the exact hwm UPDATE guard is kept because it is load-bearing. The dialect fallback is kept as a note.
- Changed the staging clear from 'delete staging rows for this run_id' to 'delete all old staging rows before loading'. Each attempt gets its own run_id, so the old rule never removed rows left by a failed attempt. Same intent, real gap fixed.
- Added the commit as a failure point in the diagram, with a rollback edge. The brief covered crashes mid-merge only, and the failure table now reads 'crash or error during commit'.
- Added a failure rule for the attempt-start insert, which the brief does not cover: it counts as a failed attempt. This is a decision, not a brief requirement.
- Moved the 06:00 staleness job and the Sunday reconciliation out of the flowchart into their own sections, since they are separate jobs. The flowchart now shows only the nightly pipeline, with its summary and terms before it and notes after it.
- Merged the attempt 1 and attempt 2 failure rows into one row, since they behave the same.
- Removed repeated 'hwm unchanged, nothing visible' wording from the steps. The failure table is now the single place for failure outcomes.
- Stated that a reconciliation reload error rolls back and leaves the day unchanged, and that the re-check still reports it. This follows from the single transaction; the brief does not state it.
- Turned 'Assumptions to confirm' into 'Open questions' and added one open question the brief does not answer: whether two attempts can overlap.

### Holes
- None.
