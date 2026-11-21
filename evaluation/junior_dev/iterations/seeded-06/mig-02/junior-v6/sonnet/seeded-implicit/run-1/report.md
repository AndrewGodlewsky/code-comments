## Review of mig-02 (junior-v6, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added who moves the flag: a person asks, the rollout tool checks the gate and sets billing_mode.
- Added one-line definitions of shadow, both and new_only, and of the shadow store contents.
- Added what the nightly job compares, the mismatch definition and the full gate numbers from the brief.
- Added what the monitor watches (2% over 10 minutes in both or new_only) and how a manual rollback starts.
- Added one line on what each rollback step does and which steps are skipped from each mode.
- Added failure handling: the rollback record contents, retry by the rollout tool, page on-call, charging stays paused.
- Restored the no-double-charge and no-dropped-charge rule and the 35-day usage log retention.
- Added an open question on who handles a flagged double charge.
- Added a charging-paused switch and said pause_charging and resume_charging turn it on and off, because the junior could not tell how the pause works.
- Said catch_up computes invoices and writes the ledger without charging, and reconcile does the charging of due amounts.
- Defined unresolved mismatch and how a mismatch is resolved, and added a resolved field on comparison_results rows.
- Defined what the 35-day limit counts from (entering new_only) and why, and that rollback is refused from day 35.
- Said a person decommissions through the rollout tool after 35 days in new_only with no rollback running.
- Stated that only one rollback record exists and a second rollback request is ignored.
- Stated that forward moves are refused while a rollback record is open, and that gate counts use only comparison_results rows after the last rollback finished.
- Added a Where state lives section and a terms list, and rewrote the document in the required order: summary, terms, diagram, modes, state, steps, failures, open questions.
- Added open questions for the retry count and delay, the rollback command form and who may mark a mismatch resolved.
- Added the term 'Stop point' and said the rollout tool records it at the move to new_only, so catch_up knows where to start (Q17).
- Changed catch_up to write ledger entries only where none exists and keep the new engine's entries, so no duplicates (Q16).
- Expanded reconcile: the ledger is the source of truth; a ledger entry without a provider charge is charged once; a provider charge without a ledger entry or a double charge is flagged, never auto-refunded (Q18).
- Stated that from both the ledger is already complete because the new engine wrote it, so the old engine just resumes (Q19).
- Spelled out how the 14 days in both are counted: from entry to both, failed comparison days do not count, a rollback restarts the count (Q20).
- Said that rollback from shadow is started only by on-call and still uses the rollback record, which blocks forward moves until it closes (Q21).
- Added unmatched provider charges to the open question about who handles flagged double charges.
- Added the stop point to the list of state kept by the rollout tool.
- Reordered into: summary paragraph, terms, diagram, modes, state location, forward moves, rollback, failure table, open questions.
- Merged the separate forward-move steps into four gate moves; folded the old_only-to-shadow note and the reset rule into the 7-day gate.
- Merged the repeated 'second request ignored', 'day 35 refused' and 'shadow errors' statements into the rollback section and one failure table.
- Cut the duplicated explanation of why the ledger is complete from both; kept it in one line under steps by start mode.
- Added to terms: ledger holds one entry per customer and billing period; rollout tool keeps evidence and sign-off; monitor starts automatic rollbacks.
- Added one clause saying the charging-paused switch is an addition because the brief names no mechanism, and that reconcile is the single place where rollback charging happens.
- Added the nightly comparison failure row to the failure table and the stop-point offset unknown to open questions.
- Restored brief facts: rollback always ends in old_only, on-call can start at any time, shadow-only manual start, 5,000 invoice minimum, 35-day retention, decommission rule.

### Holes
- None.
