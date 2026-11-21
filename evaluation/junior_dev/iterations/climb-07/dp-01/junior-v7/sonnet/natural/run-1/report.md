## Review of dp-01 (junior-v7, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Defined scheduler and orchestrator in a terms section and made the attempt counter derive from run_log.
- Added how run_id, run_date and attempt are chosen, and a new run_id per attempt.
- Stated that step 1 marks a running row older than 3 hours as failed, and that failed attempts set their row to failed.
- Added a 60-minute per-attempt timeout enforced by the orchestrator, flagged as a placeholder.
- Moved dedupe out of step 5 into the step 6 query and stated that the stage keeps all rows.
- Defined the freshness check as a succeeded run_log row for today's UTC run_date.
- Added first-run behaviour and the orchestrator-dies failure row.
- Described dashboards and alerts around 06:00 and a late commit.
- Restructured into summary, terms, state, diagram, flow, failures, reconciliation, rollout assumptions and open questions, and merged the repeated design table and step lists.
- Added an Open questions section and fixed the reconciliation step numbering in the diagram.
- Added a `kind` column (nightly or reconcile) to run_log so reconciliation's attempt count and rows stay separate from the nightly ones.
- Step 1 and the reconciliation section now say the attempt number counts rows of the same run_date and kind, and that the one-running-row index is shared across both kinds.
- Added a note that a stale-failed row cannot push a night past 3 attempts.
- Added a 'Lost commit reply' bullet: check run_log for the run_id before marking failed; the success mark shares the commit's transaction. Updated the step 6 row of the failure table to match.
- Reconciliation is now stated to be the same orchestrator run, not a separate trigger. The diagram subgraph title says so, and the Terms entry for the orchestrator covers it.
- The freshness check now reads only succeeded `nightly` rows and ignores a running reconciliation. The diagram node was updated.
- Compare section says who runs each query and that the orchestrator compares at most 30 small rows each in memory; diagram node G3 says the orchestrator compares.
- Third-attempt-failure row now says on-call may rerun by hand safely and that the 06:00 alert is still posted.
- Added an open question about the missing on-call runbook.
- Merged the two 'what starts each step' and 'what data moves where' sections' content into the step notes; the diagram already shows data movement, so the separate data-movement list was not repeated.
- Removed the repeated sentence that stated idempotence in the failure table and kept one statement under the step notes; table rows point to it.
- Shortened the summary to a few sentences and the lookback definition (30 minutes for replica lag stated once).
- Added to Step 1 a short reason for the single-running-row index (one run at a time).
- Trimmed wording in the freshness check, lost-commit and stale-row notes without dropping any rule, number or setting.
- Renamed 'How a nightly attempt works' to 'Nightly attempt: notes on the steps' since the diagram carries the flow.
- Kept all first-version facts: 02:00/06:00 UTC, 2h lookback, 90 min imports, 3 attempts 15 min apart, page on-call, #data-alerts, 30-day reconciliation with count and checksum, is_deleted, GREATEST HWM, repeatable-read, 3-hour dead row, shadow-table fallback, known 30-day limit.

### Holes
- Q7: What is the backfill start value, and what happens on the very first run when the high-water mark is that seed? Is the first extract a huge load, and do the same window and timeout apply? (author: The backfill start value is not known; it is an open question. The first run uses the same window rule, so it loads all history from the seed and is large. I added that a first run exceeding the timeout should be run by hand with a longer limit.)
- Q14: After a third failure, on-call is paged. Does on-call have a defined action, such as a manual rerun, or do they wait for the next night? Is the staleness alert from 06:00 also posted? (author: The brief defines no on-call runbook. I only stated that a manual rerun is safe because runs are idempotent, and otherwise the next night's lookback recovers the data. The 06:00 staleness alert is still posted if nothing has succeeded by then, even after the page, because the check is independent and only reads run_log. Added the runbook gap to the open questions.)
