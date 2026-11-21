## Review of dp-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Replaced the skeletal diagram, which had mostly unconnected nodes, with a full flowchart showing triggers (solid arrows), data and state reads and writes (dotted arrows), the four state tables, retries, the page, the 06:00 check and the reconciliation loop.
- Spelled out the merge logic: dedupe by order_id keeping the greatest updated_at, upsert only if the staged updated_at is greater than or equal to the stored one, soft deletes stored as is_deleted.
- Defined the staging table (wiped each run, never read by dashboards) and the watermark (single row, set to the max updated_at of the extract, advanced in the same transaction as the merge).
- Explained why the 2-hour lookback exists (90-minute bulk transactions, updated_at stamped at write time) and why duplicate extraction is harmless.
- Added a state table listing what each warehouse table holds and who writes it.
- Described retry timing and why a rerun is safe at any point, and that the page happens after the third failed attempt.
- Explained how the 06:00 dashboard refresh never sees a half-loaded night, and that the staleness alert is a separate check reading etl_runs.
- Expanded the Sunday reconciliation: what is compared, where, and how mismatched days are reloaded through the normal path.
- Marked the reconciliation failure alerting as an assumption beyond the brief.
- Replaced terse bullet fragments with short sectioned notes so a reader new to the project can follow without the brief.
- Added a short terms paragraph defining watermark, staging, and fact_orders up front.
- Diagram: renamed the retry decision to 'Did the attempt fail?' and labeled the step-to-decision arrows 'on error' so they are not read as always-taken control flow; renamed the 'Pipeline steps' subgraph to 'Nightly job'.
- Merge: watermark now set to the greater of its current value and the extract max, so it can never move backward.
- Stated that reconciliation reloads extract by creation date and do not change the watermark, and that reconciliation starts after the nightly load finishes (they share staging).
- Explained that soft deletes are ordinary writes, and that etl_runs is written outside the merge transaction so failures are recorded.
- Minor wording fixes: lookback margin, 'more than 2 hours', clearer retry timing, and paging independence.
- Fixed an inconsistency: the success mark in etl_runs is now clearly written inside the merge transaction, while start and failed records are written outside it (diagram, step 3, and table now agree).
- Fixed the diagram and text conflict on reconciliation reloads: reloads run steps 1 to 3 but skip the watermark update, now stated in the diagram edge and the notes.
- Added a 'Night complete' success path to the diagram; before, only failure paths left the pipeline steps.
- Reworded the retry decision node and its edges to 'attempts used so far' with '1st or 2nd attempt' and '3rd attempt', which is unambiguous.
- Defined 'attempt' and 'night's run' in the Terms section.
- Clarified that reconciliation starts after the nightly run ends (success or retries exhausted) and listed this as an assumption, which also avoids sharing stg_orders with a running nightly job.
- Clarified the retry timing sentence so the attempt start times are not misread as exact.

### Holes
- None.
