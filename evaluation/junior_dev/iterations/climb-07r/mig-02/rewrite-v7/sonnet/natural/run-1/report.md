## Review of mig-02 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a Terms section defining billing_mode, usage event log, billing ledger, shadow store, nightly comparison, charge key, rollback record, Gate A, Gate B and day 35.
- Merged the separate comparison, forward-moves and gates bullets into one short paragraph under the mode table.
- Moved gate definitions into Terms and diagram notes only; removed the repeated sentence about when gates are checked.
- Merged the rollback trigger rules (manual, automatic, shadow errors) into the Rollback section; they were previously split between Summary and failures.
- Cut the repeated 'after any rollback' failure bullet and folded it into the Commit step.
- Turned the failure bullets into a table and removed the duplicated shadow-error and gate-reset lines.
- Added the reason for the 35-day limit inside step 3 and why step 3 runs only from new_only; dropped the separate paragraph.
- Rewrote the Summary to describe today's system and the main flow in a few sentences, and added the decommission and no-double-charge intent.
- Kept every stated number and rule: 35-day retention, one cent, 7 days, 0.1%, 5,000 invoices, 14 days, Finance sign-off, 2% over 10 minutes, shadow errors never trigger rollback, gates reset.

### Holes
- None.
