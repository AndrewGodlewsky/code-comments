## Review of mig-02 (junior-v3, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Shortened the summary to a short paragraph and added a Terms section with one line per term (billing_mode, shadow store, mismatch, gate, freeze, due charge, idempotency key).
- Changed 'affected customers' in the freeze step to all customers, since billing_mode is global and the brief gives no per-customer scope (Q3).
- Stated that billing_mode keeps its current value during steps 1 to 3, that freeze is a rollout state and not a mode, and that nobody charges during those steps (Q3).
- Defined 'marked due' as a period with an invoice total above zero and no provider charge found, charged by the old engine in step 4 after a provider lookup (Q6).
- Added the rule that one move or rollback runs at a time, that a running rollback refuses forward moves, and that a trigger during rollback is logged and ignored (Q8).
- Described the nightly comparison in the both mode entry: new-engine ledger invoices against old-engine shadow-store invoices, per customer (Q4).
- Turned the rollback steps and failure handling into a numbered list and a table, and kept the day-35 impossibility in one row only.
- Moved unknowns (failure-rate definition, freeze visibility, gate enforcement, unresolved mismatch handling, idempotency key status, 5000-invoice threshold, storage, 35-day clock) into one Open questions list at the end. Labels such as 'proposed' were removed where no decision was made and the item is now stated as open.
- Added a Rollout controller term and said the controller runs the rollback steps, with on-call restarting a failed step by hand (Q9).
- Rollback step 1 now waits for charges already sent to the provider to finish or be looked up, and no new charge is sent during the freeze (Q10).
- Rollback step 3 and the shadow path now say that steps 1, 2 and 4 change nothing in shadow and step 3 still checks the ledger against provider charges (Q11).
- Diagram: new_only to decommissioned is now a person's approval on day 35 or later, not a clock trigger, and the diagram note says why (Q12).
- Mode descriptions: the nightly comparison pairs and the per-invoice mismatch rate are stated once, under the modes (Q13, Q14).
- Where the state lives: workers read billing_mode before each charge, not from a cache (Q15).
- Merged the rule notes into shorter bullets, cut repeated statements about the freeze, and folded the rollback-trigger rule into the failure table.
- Open questions: added step 1 wait time, flag propagation and double charge during a flip, correction of a wrongly made charge, and what decommissioning shuts down.
- Cut the separate 'What each mode does' section and folded each mode's behaviour into the numbered forward steps 1 to 5. Its wording repeated the diagram labels and notes.
- Merged the nightly-comparison paragraph into the forward steps and kept the mismatch-rate formula in one place.
- Merged the rollback prose into one paragraph above the rollback steps: no step retries itself, billing_mode keeps its value during steps 1 to 3, and due charges are delayed, not dropped.
- Rewrote the rollback steps so each stands alone and no longer refers back to the diagram or to other sections.
- Shortened the diagram labels to the essential condition and kept every transition, gate value and rollback path. Diagram form kept.
- Shortened the terms to one line each and removed the repeated explanation of freeze from the notes.
- Reduced the failure table to one line per failure and kept every row, including the 'our reading of consecutive' decision.
- Kept all ten open questions, reworded for brevity. No question was dropped and no mechanism was added. Plan intent is unchanged.

### Holes
- Q2: What does 'the new-engine charge failure rate' mean exactly: failed charges divided by what, counted from where, and what component measures it and starts the auto rollback? (author: The brief gives the 2 percent threshold and the 10-minute window but not the denominator, the measuring component, or a minimum attempt count. I have not chosen a definition. It is an open question.)
- Q7: The failure section says a failed rollback step is retried idempotently, but the idempotency key is called 'proposed'. Is it actually in place today? If not, what is stopping double charges now? (author: The brief does not say whether the idempotency key exists today. The file now says it is not confirmed. Nothing in the brief protects against double charges beyond the rule to look up the provider before any retry. Whether the key must exist before both is an open question.)
- Q14: In both, what happens to a customer whose mismatch is found: is the charge already made by the new engine, and is anything corrected for that customer, or is it only counted? (author: Checked: in both, the new engine has already charged and written the ledger for a mismatched customer, so the charge is already made. Unknown: whether anything is corrected for that customer. The brief only says the mismatch blocks the both to new_only gate. The file now says the rollout does not correct the charge, and the correction question is listed as open.)
