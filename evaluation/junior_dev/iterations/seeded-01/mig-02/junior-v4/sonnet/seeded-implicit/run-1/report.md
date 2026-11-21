## Review of mig-02 (junior-v4, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a one-paragraph summary, today's behavior, and a terms list defining each piece (flag, log, ledger, shadow store, job, monitor, tool, rollback record).
- Added a modes table showing what each engine does in each mode and who writes the ledger.
- Labelled diagram transitions with who triggers them and added the new_only to decommissioned and the 35-day limit.
- Added a forward moves section: a person runs the rollout tool, with gates; tool failure leaves the flag unchanged.
- Defined each rollback step and when billing_mode changes, and replaced 'skipped where not needed' with a table by starting mode.
- Specified the monitor trigger (above 2% over any 10 minutes, in both or new_only only) and that shadow errors never trigger.
- Defined the rollback record and replaced 'steps are retryable' with a concrete rule: rerun the failed step; reconcile checks the ledger so repeats are safe.
- Added a where-state-lives section and a failure table.
- Added open questions: 5,000 invoices per day or total, meaning of resolved mismatch, alerting on stuck rollback, who writes the usage event log.
- Added charging_paused, the setting that implements pause_charging, to Terms and step 1, with what happens to customers due while paused.
- Defined the rollback runner and stated that it runs the steps itself and reruns failed ones.
- Said the billing monitor calls the rollback runner, and that a second rollback start request is ignored while one is in progress (added to the failure table).
- Moved the double-charge guard into the ledger definition (check ledger per customer and billing period before every charge), and explained why forward moves need no pause.
- Said how engines learn the mode (read billing_mode at the start of each run, in-progress runs finish under the old mode).
- Clarified reconcile (old engine works out what is due from usage events; ledger gives the already-charged check) and catch_up (replays from when new_only began).
- Added an open question on how often billing runs start.
- Rollback record: added that the runner clears it after resume_charging, so later rollbacks can start.
- Rollout tool: added that it also refuses while a rollback is in progress, in Terms and Forward moves.
- Added a charge check (re-read billing_mode and charging_paused before each charge) so an in-progress run cannot charge after a mode change; adjusted the billing_mode term and switch_to_old step to match.
- Ledger: stated it holds at most one charge per customer and period and rejects duplicates; added as an assumption in open questions.
- Modes: noted engines do not see a flag change at the same instant and a missed charge is made next run.
- Nightly job: stated it runs once a night in shadow and both, compares per customer and billing period since last run, and that a mismatch only raises the rate.
- Rollback step failure: said the runner retries by itself; added runner-crash row and open question.
- Open questions: extended mismatch question, added runner-crash and ledger-duplicate questions.
- Removed the rule that a running run keeps its starting mode from the billing_mode term, since the charge check already covers it.
- Merged the shadow row's 'never charges, never writes ledger' into 'computes into the shadow store only'.
- Dropped the repeated 'A mismatch only raises the mismatch rate' sentence.
- Shortened Billing monitor, Rollout tool and Rollback record definitions, removing duplicated refusal and clearing rules.
- Moved the 'tool refuses' statement to the Terms definition and removed the duplicate in Forward moves.
- Removed the 'Charges at 2% failure' row from the failure table because it repeats the Rollback start rule.
- Cut the repeated 'Neither engine charges' and 'The old engine charges again' phrasing in rollback steps 1 and 5 where already stated in the terms.
- Kept the section order and the diagram unchanged.

### Holes
- Q5: What is the usage event log, and which engines read from it or write to it? How does it relate to catch_up in rollback? (author: It is the input both engines read; it keeps events for 35 days. catch_up replays from it the events the old engine skipped in new_only, which is why rollback is only possible within 35 days. Who writes to the log is not known and is listed as open.)
- Q13: How do the engines learn the mode? Do they read the flag on each billing run or on a schedule? What happens to a run in progress when the flag changes? (author: Decided that each engine reads billing_mode at the start of each billing run and a run in progress finishes under its starting mode, with the ledger check preventing duplicates. How often runs start is not known and is now listed as open.)
- Q22: What starts the nightly comparison job, and how does it know which billing period or day's invoices to compare? What does a mismatch lead to besides the rate count? (author: Decided: it runs once a night in shadow and both and compares invoices per customer and billing period computed since its last run. A mismatch only raises the mismatch rate. What a mismatch leads to beyond that, and what makes it resolved, is not known, and is in the open questions.)
