## Review of mig-02 (junior-v2, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Moved the person's old_only write (await_flag) before resume_old. The old engine does not charge in both or new_only, so the previous order could not work.
- Defined the 0.1% mismatch rate as a share of invoices per UTC day, and made a day count only when its comparison completed.
- Set the idempotency key to customer ID plus billing period ID, shared by both engines, and recorded before the first call.
- Defined the 2% failure rate, who computes it, and that zero-attempt windows never trigger.
- Defined reconciliation per period against the provider, including the three ownership outcomes.
- Defined replay as a no-charge computation from a stored new_only cutoff timestamp.
- Stated that the kill switch blocks new-engine charges only, and that the old engine is held by its mode.
- Stated that the system checks gates when a forward-move write arrives.
- Merged the rollback rules into the Rollback section and removed the duplicated rollback description.
- Moved the decided items out of Open points: state storage, freeze order, the UTC time zone, and how sign-off is recorded.
- Kept the revised document within about 1.5 times the original length.
- Kill switch now blocks ordinary runs of both engines until resume_old clears it, so the old engine cannot charge right after old_only is written (Q11). The earlier statement that the old engine needs no switch is superseded.
- Rollback steps now name the rollout controller as the component that runs them, and the controller's form is listed as an open point (Q12).
- Reconcile_ownership now separates three outcomes: success, final failure or no record, and no final outcome yet. Only the second is charged in resume_old, and the third holds the period (Q15).
- Added a rule that mode changes apply to runs that start after the write, and that the new engine checks the provider by key before its first charge (Q14).
- Decommissioned is now a person's audited move on or after day 35, and the diagram labels say who makes each forward move (Q13).
- Both-to-new_only now states that a person closes each mismatch and that new mismatches do not reset the 14-day count (Q16).
- Added new-engine attempt and failure counts to the rollout record, because the 2% rule depends on them.
- Merged the two failure-handling notes on rollback and the repeated rollback detail, and shortened the charge and state sections, so the file stays within about 1.5 times its first length.
- Open points now also cover the controller's form, the provider's pending-outcome and same-key behaviour, and what retiring the old engine involves.
- Merged the two statements that billing_mode changes only by audited, person-initiated write (gates section and state-location section) into one line under the moves list, and dropped the repeat.
- Folded the separate 'every forward move is an audited write' gate bullet into the forward-moves bullet, so the gate-check rule is stated once.
- Replaced the repeated rollback-trigger wording in the mode descriptions and the rollback section with one 'Start' paragraph that defines the 2% rate, the zero-attempt rule and that automation never writes billing_mode.
- Removed the repeated 'without charging' phrasing from the old_only, shadow and both descriptions, and stated the nightly comparison definition once, under the mode list.
- Merged the 'from shadow there is nothing to replay' and 'from both the shadow invoices are current' notes into the source_check step, instead of a separate paragraph at the end.
- Grouped the rollback Effect rules (kill switch, gate reset, resume-at-last-step) into one short block before the steps.
- Kept all six open questions together at the end under one heading, with their wording shortened but their substance unchanged.
- Left the Mermaid diagram unchanged, since it is the required artifact and the simplification did not change any transition.
- No mechanisms were added or removed and no rule changed. The only wording change in substance is that the comparison is stated as running in shadow and both, which is what the brief says.

### Holes
- Q12: What is the rollout controller? Is it a separate service, a scheduled job or part of the billing workers? What starts it, and what happens if it is down when a rollback is needed? (author: The brief does not say what the rollout controller is, and it is not yet written. The file now says the controller computes the rate, sets the kill switch and runs the steps, and lists its form as an open point. If it is down, no rollback step runs, so automatic rollback cannot start, while the charge path keeps writing attempt and failure counts to the rollout record. Whether it is a service, a scheduled job or part of the workers is not known.)
