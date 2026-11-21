## Review of mig-02 (junior-v7, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a Terms section defining billing_mode, usage event log, ledger, shadow store, nightly comparison job, mismatch, charge failure rate, billing monitor, rollout tool and rollback record, so a newcomer does not need to ask what they are.
- Added transition labels to the diagram that say who triggers each move and the day 35 limit on rollback from new_only. The diagram shape and the rolling_back composite are unchanged.
- Rewrote the rollback steps so switch_to_old does not charge. The old engine starts charging only at resume_charging, after reconcile, which prevents charging before the ledger is checked.
- Added a table showing which rollback steps run from shadow, both and new_only, so skipped steps are explicit.
- Defined the rollback record and the retry rule: each finished step is marked, retries resume at the first unfinished step, and reconcile checks the ledger before each charge.
- Defined a clean comparison day and the rule that a night with no comparison breaks the 7-day count.
- Added a failure table covering every failure case in the brief and the first version.
- Added a Decommissioning section stating that day 35 counts from entering new_only and that there is no rollback after day 35.
- Moved gate rules into their own list and kept every requirement, limit and number from the brief and first version. Open questions are listed at the end.
- Added the charging-engine mark to the rollback record and to the switch_to_old step, which answers Q11.
- Pause step now says the new engine writes no new ledger rows and that due charges stay in the ledger uncharged until reconcile, which answers Q12 and Q16.
- Reconcile step now states the amount rule: a ledger period already charged is left alone, a difference is recorded as a mismatch, and a due charge is charged at the old engine's invoice amount. This answers Q13.
- Added the definition of an unresolved mismatch under the both-to-new_only gate, which answers Q14.
- Added the rule that only one rollback runs at a time, which answers Q15, in the failure table.
- Added that the nightly comparison does not run in new_only and that no gate applies there, which answers Q17.
- Split forward moves from rollback steps and gave each rollback step its trigger, action, data kept and failure handling.
- Moved the per-step failure handling into the steps and kept the table for failures that are not a step, to remove repetition.
- Added terms for charging engine, due charge, mismatch rate and comparison_results, and merged the nightly job definition into one term.
- Added the no-gate note for old_only to shadow and the rule that rollback-period comparison rows never count toward a gate.
- Added an open question about who marks a mismatch resolved, and one about the uncharged-period amount, and removed no earlier open question.
- Rollback steps intro: added that the rollout tool runs the steps in order, starting each once the previous one is marked done (Q18).
- switch_to_old: replaced 'does not charge yet' with the rule that the old engine charges only the due charges reconcile finds until resume_charging, removing the contradiction with reconcile (Q19).
- catch_up: added that events arriving after catch_up finishes are computed by the old engine as they arrive, as in both, until resume_charging (Q22).
- reconcile: added that in both the old engine has already computed invoices into the shadow store, so a period the new engine never wrote to the ledger still has an invoice to charge (Q20).
- resume_charging: added that the new engine turns off and writes nothing more to the shadow store (Q21).
- Forward move: added that nothing else is switched by hand and each engine reads billing_mode (Q23).
- Open questions: added where the 14-day and day-35 start points are recorded and whether a night with no comparison in both resets the count (Q24).
- Open questions: added whether charges that fall due between reconcile and resume_charging are charged, and by which step (Q22 gap).
- Summary rewritten as three sentences: how billing works today, how the forward moves and rollback are gated and retried, and why (gradual, reversible, never a double charge).
- Terms list now defines every name a newcomer would not know: gate, clean day, unresolved mismatch, charging engine, due charge, rollout tool, billing monitor, rollback record. Removed the Q/R-style references and the duplicate storage notes from the terms.
- Forward moves and gates merged into one section. Kept the rule that moves never skip a mode and that the rollout tool refuses a move whose gate has not passed. Kept the rule that nothing else is switched by hand.
- Restored the brief's wording for on-call: it may start a rollback at any time, subject to the 35-day limit. The previous draft had narrowed this to 'before day 35' for every mode.
- Rollback steps each now state what starts them, what they do, what data they keep, and what happens on failure. Reconcile's cases are listed as four short points. Stated that the rollout tool runs the steps itself and resumes at the first step not marked done.
- Duplicate rules merged: the 7-day reset after rollback is stated once, under After a rollback. The 'reads the rollback record' and 'retryable' statements now appear once each.
- Merged the two open questions about the 14-day start and the no-comparison night in both into one. Kept all other open questions from the previous version, unchanged in meaning.
- Failure table keeps every row from the previous version and adds the rollback-step failure row. Decommissioning and where-state-lives sections added as the brief's format asks, with the facts stated once each.
- No plan behaviour was changed. The rounds' decisions (A1 to A24) are carried into the file as written, and the unknowns in A24 and A22 stay open questions rather than new rules.

### Holes
- Q24: The 14-day gate counts days in both. Where is the start of those 14 days recorded, and does a day with no comparison in both reset the count like it does in shadow? (author: The brief does not say where the start of the 14 days is recorded, and the file names no place for it. The brief also gives no reset rule for a night with no comparison in both. The 0.1% clean-day rule and the no-comparison-is-not-clean rule are written only for shadow. I did not decide either point. Both are now open questions, along with the matching start point for the day-35 count.)
