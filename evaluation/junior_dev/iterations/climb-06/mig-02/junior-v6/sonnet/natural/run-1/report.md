## Review of mig-02 (junior-v6, author sonnet, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Added a Terms section defining old/new engine, usage event log, ledger, shadow store, charge, config service, rollback record, gate and mismatch (Q1, Q2, Q8).
- Defined a charge as a provider call plus a ledger write keyed by customer and period, and said how each engine knows whether it may charge in both (Q2).
- Said forward moves are made by a person changing billing_mode and that the person checks gates by hand (Q3).
- Spelled out in freeze that workers read the rollback record to stop charging and how in-flight and unknown charges are handled (Q4).
- Said in reprocess where recomputed invoices go and how already-charged periods are skipped (Q5).
- Set the switch_back order: flag to old_only, new engine off, then clear the record; charging resumes automatically (Q6).
- Moved the automatic rollback trigger into the mode notes and added open questions for failure-rate measurement and decline handling (Q7).
- Stated what happens to the nightly comparison after rollback (Q8).
- Added open questions about config propagation and the tool used for forward moves; merged the summary and gate notes into the new layout.
- Added terms for the rollback controller and the affected window.
- Said the rollback controller runs the rollback steps, advances on success and pages on-call on failure.
- Defined the reconcile window as entry into both up to freeze, for both origins.
- Explained why a rollback from both skips reprocess, and said the old engine recomputes due periods from usage events instead of charging from shadow-store invoices.
- Described the pin as owned by the controller and released when the rollback record is cleared.
- Made the shadow rollback explicit: no rollback record, switch_back only, new engine's shadow writes end, shadow store kept for audit; diagram now says record cleared if any.
- Stated where the entry time into new_only is recorded and how the rollback trigger uses it to refuse after day 35.
- Clarified that decommissioned is not a flag value, in the failures section and a diagram note.
- Added open questions 7 (pin mechanism) and 8 (limit on paused charging and on-call override).
- Moved the usage event pin from reprocess into freeze (same step as writing the rollback record) to close the day-34 expiry hole; updated the diagram edge, day-35-during-rollback line and open question 1.
- Added a rule for periods in progress at a forward move: the mode read at charge time decides, with the key check as the safeguard.
- Stated that reconcile retries and pages on-call when the provider cannot answer, and added it to the failure list.
- Defined an unresolved mismatch as one a person has not marked resolved, with open questions 9 (who and where) and 10 (settle time in freeze).
- Clarified that a rollback trigger must be accepted before day 35 and that the controller keeps retrying a failed step.
- Rollback record now also stores the two reconcile lists, and a restarted controller reloads it instead of redoing steps (Q21).
- Reprocess is now a compute-only run of the old engine writing to the shadow store, with nothing charged; added open question 11 on whether reprocess is needed (Q22).
- Stated that periods due during the pause are computed and charged by the old engine after switch_back from events that stay in the log (Q23).
- The trigger now creates the rollback record create-if-absent as the single-rollback guard, including for shadow origin where it does not pause charging; spelled out simultaneous triggers (Q24).
- The pin now happens at the start of freeze for both origins (everything still in the log when origin is both), and the diagram and day-35 text were updated to match (Q25).
- Diagram: reconcile edge says the lists are saved in the record; reprocess edge says compute-only; switch_back always clears the record.
- Added a controller-restart row to the failure section and a note on the small gap between trigger and pin in open question 1.
- Merged the 'Forward moves', 'Periods in progress', and charge-key explanations into the Charge term and one forward-moves bullet.
- Moved the rollback trigger rules and day-35 decommission rule into the mode notes so the brief's rules sit together; kept all numbers (35 days, 1 cent, 7 days, 0.1%, 5000, 14 days, Finance, 2%, 10 min).
- Added a Pin term, a Mismatch-unresolved definition and a short Rollback controller term; defined Affected window and Gate.
- Resolved the contradiction between 'no record in shadow rollback' and trigger step: the record is always created, and only pauses charging for origin both/new_only.
- Turned the failures list into one table and added controller-restart and provider-down rows.
- Merged repeated 'step fails / retry / page on-call' text into one paragraph before the steps.
- Cut: the long defence of why the pin sits in freeze, the repeated explanations of the per-key check, and the second copy of the failure behaviour inside steps.
- Merged open questions on pin implementation and in-flight timeout wording; added question 12 for the unverified recent-periods assumption from rollback from both.
- No separate build/rollout section was added because the brief and document contain no build plan; the document covers only how the system runs.

### Holes
- Q1: What is the config service, and how do the engines and workers learn that billing_mode changed? Is it polled or pushed, and how long can workers see a stale value? (author: The config service holds billing_mode. Whether workers poll or are pushed changes, and the maximum staleness, are not known. Added as an open question. The per-key ledger and provider check before every charge is the safeguard against a stale worker double-charging.)
- Q7: Automatic rollback: who or what measures the charge failure rate over a 10-minute window, and what counts as a charge failure (declines versus system errors)? What if a high rate is just customers' cards declining? (author: Not decided who or what measures the rate, and whether card declines count as failures. The brief only says charge failure rate above 2% over any 10 minutes. I would want only system and provider errors counted, but I have no basis from the brief, so it is an open question.)
- Q15: If a rollback step keeps failing, charging stays paused. Is there any limit on how long customers can go uncharged, and what does on-call do to unblock it? (author: The brief gives no limit on how long charging may stay paused, and no override for on-call. The plan assumes on-call fixes the cause and the controller's retry then succeeds. Charges are delayed, never dropped. Added as an open question.)
- Q18: What makes a mismatch 'unresolved' for the both to new_only gate? Who investigates and marks one resolved, and where is that recorded? (author: The brief says only 'no unresolved mismatches'. I assume a person marks a mismatch resolved after investigating, but who does it and where it is recorded is not known. Added as an open question.)
- Q20: During freeze, how long are in-flight charges given to settle or time out, and what if the provider is slow or down so reconcile cannot get an answer by key? Does reconcile block, or retry in that step? (author: How long in-flight charges get to settle is not known; added as an open question. The behavior I decided: if the provider cannot answer, reconcile does not guess or skip. It keeps retrying in that step and pages on-call, and charging stays paused so nothing is double charged or dropped.)
