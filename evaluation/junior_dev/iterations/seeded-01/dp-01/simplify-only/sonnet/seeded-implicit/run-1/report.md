## Review of dp-01 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the thin bullet list into a newcomer layout: summary, terms, diagram, numbered steps, retries/alerts, reconciliation, open questions.
- Completed the flowchart: added edges and labels for data movement, state, retry, paging, the 06:00 check and reconciliation; it previously had unconnected nodes.
- Merged the one-line bullets (incremental, merge, soft deletes, retries, reconciliation, deadline) into the step table and sections instead of repeating them.
- Replaced separate mechanisms for watermark and load with one: a single warehouse transaction does merge, advances the mark and marks the run succeeded.
- Kept retry handling simple: re-run from step 1, no locks or takeover rules; reconciliation failures just alert and wait for next Sunday.
- Moved unresolved matters (transaction support, how Sunday detects the load, 06:00 overlap) into Open questions.
- Added a note that rollout and build are not covered; no rollout section was added since the brief does not ask for one.

### Holes
- None.
