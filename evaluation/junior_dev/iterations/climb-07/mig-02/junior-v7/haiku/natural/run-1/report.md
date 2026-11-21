## Review of mig-02 (junior-v7, author haiku, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Moved the due-but-uncharged list build from step 3 to step 5, after catch-up. Reason: from new_only, invoices for skipped events do not exist until step 4 runs, so an earlier list would miss them.
- billing_mode now changes to old_only at the start of step 5, before the old engine charges. Reason: the old engine does not charge in both or new_only, so the flag must change before it can charge the due list.
- Added a freeze marker in the rollout record. Reason: freeze must stop charges at once without changing billing_mode during steps 1 to 4.
- Step 4 writes catch-up invoices to the ledger and charges nothing. Reason: the brief requires the old engine to reprocess before taking charge, and charging at catch-up would mix the steps.
- The due list is built from ledger invoices only. Reason: shadow invoices are never charged, so they must not feed the list.
- Defined the rollout controller and said that only it writes billing_mode, with the person's approval as its input. Reason: the brief says only a person makes forward moves.
- Defined charge failure in the terms, including a timeout until its outcome is resolved.
- Added open questions 7 to 10 for gaps the answers exposed: the approval tool, the owner of the usage event log, whether the 5,000 count is cumulative, and where the old engine's queue is stored.
- Added the 'Ledger invoice' and 'Resolved mismatch' terms, and open question 11 on who investigates mismatches (Q9, Q10).
- Step 5 now charges the existing ledger invoice as written, with its version and key, and does not recompute it (Q10).
- Step 1: the new engine checks the freeze marker before sending each request, a sent request is not cancelled, and its outcome goes to step 2 (Q11).
- Step 5: the flip waits until every worker reads old_only, then the freeze marker is cleared before the old queue runs (Q11, Q13).
- Step 3 now says where the charged-period mark is stored and how the old engine reads it (Q12).
- Added a rule that the old engine charges only in old_only, or in step 5 after the flip is confirmed (Q13).
- Added a failure row for a worker that still reads both during the flip (Q13).
- Missed nightly run row now says the controller records the missed run, and open question 12 covers who runs and who is alerted (Q14).
- Diagram rb_handover label updated to match step 5 (Q13).
- Rules: the old engine charges in old_only and shadow; the earlier line said only old_only, which contradicted the brief (Q15).
- Step 1 (from shadow): the flip needs no worker wait because the old engine charges the same way in shadow and old_only (Q15).
- Step 1 (from both or new_only): added that periods coming due during steps 1 to 4 wait for step 5 (Q16).
- Step 2: added handling for a provider lookup with no record and for a lookup that does not answer, using the same key and the existing queue (Q20).
- Step 4: stated that how catch-up invoices relate to existing new-engine invoices is open, and added open question 13 (found while answering Q18).
- Step 5: stated that the ledger invoice wins over the shadow invoice, the due list is held in the rollout record, and the rollout rests at old_only until a person approves shadow (Q17, Q18).
- Terms: added charge record, gate, streak, mismatch rate, due list and day 35; merged the mismatch and resolved-mismatch definitions.
- Modes: rewrote the mode descriptions once, after the diagram, and stated where the rollout state lives; added that the new engine charges only in both and new_only.
- Failure table: added rows for a provider with no record of the key, an unanswered lookup, and a period due during steps 1 to 4; merged the two day-35 rows into one.
- Open questions: extended 5 (how long the provider keeps keys), 7 (what on-call sees when starting a rollback), 9 (mismatch rate reading) and 10 (interim storage of the due list); added 13.
- Cut: repeated the rollback rules that were stated in more than one section, and replaced references to numbered open questions with the topic names. All brief requirements were kept.
- Added a Worker term to Terms, since step 5 and the failure table say every worker and the brief only says billing workers run the old engine.
- Step 5 now says the wait for every worker to read old_only has no timeout and the rollout stays on the rollback path until it ends.
- Step 5 now says how a failed or timed-out due-list charge is handled and that it does not trigger another rollback.
- The new_only gate now says unresolved mismatches are checked on the day of approval and the 14-day count does not restart.
- The rollback steps intro now says only one rollback runs at a time, and the failure table has a row for a second start or trigger.
- Added open question 14 for how the controller learns each worker reads old_only and who is alerted when one does not confirm.
- Summary rewritten as three sentences: how the old system works today, how the rollout moves through modes, and why the shape keeps rollback safe.
- Added a Terms section defining every name a newcomer would not know, in one line each. Merged the mismatch, mismatch-rate and resolved-mismatch definitions, and merged ledger and ledger invoice into one term.
- Diagram kept as a stateDiagram-v2 with the same states, transitions, choice node and rollback paths. Labels shortened to step names, with the detail moved to the step text. Removed the percent-sign characters from diagram labels.
- Modes section now carries each mode's behaviour and its gate. Each gate is stated once, in the mode it leaves.
- Merged the separate rules text into one Rules section covering flag reads, who charges in each mode, the freeze marker, and the single-writer rule. Removed the repeated restatements of the flip rule.
- Rollback section rewritten as five numbered steps, each with its start, action, data and failure. Added the rule that a rollback from shadow runs step 1 only.
- Folded the answers into the steps where they apply: the approval is recorded and then the controller writes the flag; the freeze marker is cleared in step 5; the due list is built after catch-up; the ledger invoice is charged as written, not recomputed; the ledger charge record is the step 3 mark; the 14-day gate's mismatch check is made on the approval day; one rollback runs at a time.
- Failure table consolidated into one table with one row per situation. Added rows for the provider-has-no-record and lookup-no-answer cases, the due-list charge failure, and the manual start in old_only.
- Added a note to the due-list failure row that the brief sets no limit on the wait in steps 1 to 4.
- Kept all 14 open questions from the previous version, reworded in plain terms. Folded the answers' open items into them: the provider key retention (5), the timeout and denominator for the 2% rate (4), the day-35 log owner (8), the mismatch investigation (11), the nightly job's scheduler (12) and the worker-confirmation method (14).
- Labelled the double-charge guard as a requirement this document adds, since the brief does not state it. Kept the streak-reset-on-missed-run rule labelled as a proposal.
- Removed codes such as R3 and Q7, and the internal cross-references, so each step stands alone.
- Did not add a lock, lease, retry queue or takeover mechanism. The brief does not require one. The wait in step 5 uses the existing worker-read check.
- Cut the first version's build-facing material. The file describes how the rollout runs, and it has no separate build or rollout-operations section, because the brief gives none.

### Holes
- Q8: In new_only, what is the '35-day log' of usage events, who keeps it, and why does the old engine need those events to catch up? (author: The brief says the usage event log is kept for 35 days, but it does not name who keeps the log. That is open question 8. The old engine needs the skipped events because it computes invoices from usage events. In new_only it stopped, so it has no invoices for events since entry. Without reprocessing, the old engine cannot bill those periods, and after day 35 the events are gone.)
- Q14: Who or what runs the nightly comparison job, and who notices when it did not run? (author: The brief does not say who schedules the nightly job or who is notified when it does not run. The file records the missed day, which resets the streak. Who runs the job and who is alerted is open question 12.)
- Q21: In step 5, how does the controller know that every worker reads old_only? Do workers report back, or does the controller poll something? (author: The brief does not say how the controller learns that every worker reads old_only. Workers reporting their mode is one possible way, but that is a mechanism the brief does not state. I did not invent one. The file now says the wait has no timeout. The reporting method is added as open question 14.)
