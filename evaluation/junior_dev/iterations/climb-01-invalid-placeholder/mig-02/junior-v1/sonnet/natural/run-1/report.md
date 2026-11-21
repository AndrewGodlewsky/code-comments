## Review of mig-02 (junior-v1, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a 'Who does what' section naming the rollout controller, how advancing is gated, the failure monitor, and how rollback steps advance (Q1, Q2, Q3).
- Step 1 now defines in-flight and the freeze marker the new engine checks (Q4).
- Step 2 now says a provider-confirmed charge missing from the ledger is recorded as charged, never retried (Q5).
- Defined the shadow store and the compare matching key under the mode table (Q6).
- Step 6 now says the old engine scans the ledger for due periods without a charge, including ones the new engine never started (Q7).
- Step 3 now says skipped events are those in the usage event log since entering new_only (Q8).
- Open question 3 extended to cover what counts as a failed charge; added Open question 6 on the matching key.
- Added step 7 CloseRecord (in diagram, steps and state notes) so the freeze marker and record end with the rollback; answers Q9 and Q14.
- Turned the rollback steps into a table with a 'Done when' column per step; answers Q11.
- Failure monitor now does nothing while a rollback record is open; answers Q12.
- Step 2 now says what happens when the provider does not answer and that it waits for every charge to be recorded; added Open question 7; answers Q10.
- Step 6 now explains why no new-engine charge can be missed; answers Q13.
- ResetGates now records a reset time and gate counters count only results after it, so old shadow store contents do not matter; added a sentence saying nothing else is needed before old_only to shadow; answers Q14.
- Step 3: stated that the old engine runs in compute-only mode while the flag is still new_only, writes invoices to the shadow store by customer and billing period, and neither charges nor writes the ledger; updated its done-when.
- Mode table: new_only old-engine cell now notes the controller can still run it for step 3.
- Step 6: says it charges from the step 3 invoice (matched by customer and billing period), computes one if missing, and writes invoice and charge to the ledger.
- Who does what: added a line on how on-call starts a manual rollback through the controller, with trigger manual; the failure monitor line now says trigger automatic.

### Holes
- Q2: What component measures the charge failure rate and starts an automatic rollback, and what does it count as a failed charge? (author: The brief does not say which component measures the rate or what counts as a failed charge. I placed the monitor inside the controller (decided), and assume a failed charge is one the provider rejects or that errors out. The exact definition and minimum volume are not known; added to Open question 3.)
- Q10: What resolves an unconfirmed charge, for example when the payment provider does not answer? Does step 2 wait until every charge is resolved before moving to step 3 or 4? (author: If the provider does not answer, the controller keeps asking and pages on-call, and a person decides. Step 2 does wait until every charge is recorded as charged or not charged before moving on, which is what prevents double charges. The wait time before paging and who exactly resolves it are not in the brief; added as Open question 7.)
