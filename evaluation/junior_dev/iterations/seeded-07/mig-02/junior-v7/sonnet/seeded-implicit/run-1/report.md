## Review of mig-02 (junior-v7, author sonnet, seeded-implicit)

Rounds: 6. Ended: cap.

### What changed
- Rewrote the file in the skill's order: summary, terms, diagram, modes, gates, rollback, decommissioning, failures, open questions.
- Defined rollout tool, billing monitor, shadow store, nightly comparison job and rollback record in a terms list (Q1, Q4, Q9).
- Added a modes table stating which engine computes, writes the ledger and charges in each mode (Q2, Q5).
- Stated the gate numbers in full: 7 consecutive days, mismatch under 0.1%, at least 5,000 invoices, one-cent mismatch, 14 days with no unresolved mismatches plus Finance (Q3).
- Stated the monitor trigger: above 2% over any 10 minutes in both or new_only, with shadow errors only recorded (Q4).
- Described each rollback step and which steps run from shadow, both and new_only (Q6, Q7).
- Defined retry behaviour and the stuck-rollback outcome in a failures table (Q8).
- Added decommissioning section with counting start and its reason, separate from the 14-day gate (Q10).
- Added transition labels to the diagram (person, manual or monitor, gate, day 35).
- Added an Open questions section for retry limits, decommission scope and where data stores live.
- Stated that rolling_back is not a billing_mode value and billing_mode keeps the starting mode until switch_to_old (Q11).
- Added that invoices due during pause_charging are held and handled by reconcile (Q12).
- Added that the charging engine may keep computing until the flag changes and workers read the flag to stop it (Q13).
- Defined reconcile's source of invoices and that it writes a missing ledger entry before charging (Q14).
- Added a crash-recovery row: nothing auto-restarts; a person or the monitor reruns the tool, which resumes from the rollback record (Q15).
- Defined unresolved mismatch in the terms and noted gate 1 uses a rate; added open question on who resolves (Q16).
- Added that an existing rollback record means a new start resumes it, plus a failure row and open question on atomic creation (Q17).
- Clarified in terms that the rollback record's existence means a rollback is in progress, and that both engines read the usage event log.
- Rollout tool term now says it reads comparison_results and computes the gate numbers itself each run (Q21).
- Added a Charge record term: the ledger entry also records whether a period was charged (Q18).
- Added a paragraph under Modes: whichever engine charges checks the charge record first, which prevents double charges when the flag moves forward (Q19).
- Reconcile now charges only if the charge record shows no charge, using the defined term (Q18).
- Gate 2 now notes that how the tool learns of Finance sign-off is not decided (Q20).
- Added two open questions: where Finance sign-off is kept and checked, and whether the ledger can hold the charge record.
- Added a `charging_paused` marker to the rollback record and defined it in Terms, answering how charging is paused and who sets and clears it.
- pause_charging now creates the rollback record and sets the marker; resume_charging clears the marker and deletes the record, which ends the rollback.
- Step 2 now says charging stays paused until step 5, so a worker with a stale flag cannot charge.
- Rollback now refuses to start from day 35 in new_only or after decommissioning, and alerts a person; added the diagram label, a Failures row and a line in Rollback.
- Added an open question about what schedules invoice computation and decides when a billing period is due.
- Added mode_entered_at term, set by the rollout tool, so days in both and new_only have a recorded source (Q28).
- Rollout tool now refuses forward moves while a rollback record exists, and writes billing_mode and mode_entered_at (Q29); added a Failures row.
- Rollback record is now created at rollback start and deleted after the last step by the tool, for every starting mode, not by pause_charging/resume_charging (Q27).
- catch_up now writes invoices to the shadow store; reconcile always reads from the shadow store (Q31).
- switch_to_old also sets mode_entered_at; decommissioning counts from mode_entered_at.
- Open questions: added alerting who/how (Q32); sharpened the reconcile differing-invoice question (Q30); split worker-notice-speed into its own item.
- Rollout tool term: one invocation runs all remaining steps and exits; rerun resumes (Q33).
- Rollback record term and start paragraph: also stores the starting mode's entry time, since switch_to_old overwrites mode_entered_at before catch_up needs it (Q36, a real bug fix).
- catch_up step: states which events were skipped, since new_only was entered (Q36).
- Charge record term: written only on successful charge; reconcile step: covers periods where the new engine failed to charge and is the only charger during rollback (Q34, Q38).
- resume_charging step: old engine's normal run charges later periods, still checking the charge record (Q34).
- Added line that the new engine's ledger entries and charges are left as they are after rollback (Q35).
- Gate 1: a night with no comparison results does not count; added matching Failures row (Q37).
- Open questions: added unknown-outcome charge attempts and whether the 5,000 minimum is a total or per night (Q37, Q38).
- Rewrote the opening as a three-sentence summary: how billing works today, the four-mode flow, and why (charge-record check prevents double charges).
- Merged the separate mode_entered_at, rollout tool, and gate-check explanations into the Terms; added definitions for charge record, rollback record, charging_paused, shadow store and unresolved mismatch.
- Cut the repeated per-mode and per-engine descriptions into one Modes table and removed the duplicated 'which engine writes where' prose.
- Merged the 'second rollback' and 'forward move during rollback' failure rows into one row; merged several open questions (ledger charge record + config service read; timeout + idempotency keys).
- Merged the separate pause_charging/resume_charging explanations into the steps themselves; resume_charging now also states record deletion ends the rollback.
- Folded the 35-day no-rollback rule into Decommissioning and the rollback start rule, removing the repeat in the Rollback section.
- Put Gates in their own section, restating forward moves are in order with no skipping, with the gate 1 rate definition and the strict day-counting rule.
- Restored from the brief/first version: 'before day 35' limit on manual rollback, shadow errors never trigger rollback, gates reset after rollback, 35-day log retention, one-cent mismatch definition.
- Dropped the 'Pieces involved' list (covered by Terms) and the 'steps are retryable' note (now in Failures).

### Holes
- Q10: The 35 days: counted from which moment, and what is decommissioned (engine code, data, or both)? How does this relate to the 14-day gate? (author: Counted from entering new_only, per the brief. Reason for 35: it matches the event log retention, so catch_up needs the events. It is independent of the 14-day gate, which is time spent in both earlier. What exactly decommission removes (code, data or both) is not known; added as an open question.)
- Q16: What does an unresolved mismatch mean, and who resolves one and how? Is it different from the mismatch rate used in gate 1? (author: An unresolved mismatch is one over a cent in comparison_results not yet marked resolved, as opposed to gate 1's rate over the window. Who resolves one and how is not specified in the brief and I do not know; added as an open question.)
- Q20: How does the rollout tool know Finance has signed off for gate 2, and where is that sign-off kept? (author: The brief says Finance sign-off is required but not how it is recorded or checked. I do not know where it is kept. I did not invent a mechanism; added as an open question.)
- Q25: In both and new_only, who decides which invoices get computed and when a customer's billing period is due? Is it a scheduled worker run, or triggered by each usage event? (author: The brief does not say whether invoicing is a scheduled worker run or triggered by usage events, and I do not know how the current workers do it. I assumed the new engine follows the old engine's schedule. It does not change the state machine; added a short open question.)
- Q30: In reconcile for a rollback from both, the old engine's invoice may differ from the one the new engine already wrote to the ledger. Which is charged or kept in that case? (author: Not decided and not in the brief. A period already charged is never charged again, whichever invoice was used. What to do for an uncharged period where the ledger holds a differing new-engine invoice is unknown; I did not invent a rule. Sharpened the open question.)
- Q32: Who is alerted and how when retries keep failing or when a rollback is refused after day 35? (author: Who is alerted and by what channel is not in the brief and I do not know the existing alerting. I did not invent one; added to the open question about retries and alerting.)
- Q38: While charging is paused for a rollback from new_only, customers' payment attempts that fail on the new engine's side (the cause of the monitor firing) -- are those failed charges retried by reconcile, and how does it tell a failed charge from no charge? (author: I assume the charge record is written only when a charge succeeds, so a failed attempt leaves no charge record and reconcile charges that period again via the old engine. That is a stated assumption, not verified. I do not know how an attempt that timed out with an unknown result is told apart from no charge, nor whether the payment provider supports idempotency keys; added an open question and did not invent a mechanism.)
