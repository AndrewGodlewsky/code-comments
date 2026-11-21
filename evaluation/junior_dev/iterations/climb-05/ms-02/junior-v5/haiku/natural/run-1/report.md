## Review of ms-02 (junior-v5, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a summary of how the current in-process worker works, then a terms section that defines each term in one line.
- Defined the sweeper: it runs in the monolith relay loop once a minute and has three page conditions. Step 9 now uses check 3 for its stuck-row check.
- Stated what broker confirmation means and what the relay does if it never arrives.
- Changed the step 6 reconciliation to count only route = service rows created more than 1 hour ago. The old count included monolith rows, which would show a false mismatch during a flip.
- Added a rule that every instance must run the step 2 build before step 6. An older build would otherwise send service rows through the old worker.
- Specified the step 5 test rows: inserted with route = service, using the shipping_update template, addressed to a test mailbox, and excluded from reconciliation.
- Stated the step 7 latency clock as sent_at minus the monolith created_at, since the relay message carries created_at.
- Stated that a failed event sets the monolith row to failed, that no automatic retry runs, and that on-call handles recovery.
- Added open items for the broker retention versus the 30-day jobs retention, the worker thread stopping on non-MailRelay errors, and the unnamed broker product and flag store.
- Merged the repeated failure notes into one failure table, and cut duplicate rules. The design decisions and gates are unchanged.
- Step 7 (reconciliation): the service now publishes a daily count to a new notification.summary topic, and the monolith compares it with its own count. The brief says the broker is the only channel, so neither side reads the other's database. The check now runs once per closed UTC day and pages when the summary arrives, instead of 'a mismatch lasting past 1 hour'.
- Flow step 4 (send): clarified that a retryable error clears the lease in the same update, and that no event is written on a retry, so the monolith row stays pending with its old attempts count until the final event.
- Added a reconciliation runbook section that tells on-call how to find and fix each missing or unapplied row, and that the ids are copied by hand.
- Split the document into 'How it runs' (summary, terms, flow, failures, runbook) and 'How we roll it out' (steps 1 to 9, rollback), as the skill asks. Defined Job and Notification Service terms and expanded the sweeper definition inline. Replaced the step-level references to the flow with plain statements.
- Rollout step 3 and step 4 now point to the flow's Publish, Record, Consumer, Sender and Events steps instead of repeating them. Failure table row 'crash mid-batch' reworded to the per-row commit from step 1. Added a reconciliation-mismatch row to the failure table, and added the runbook's republish case to the jobs-retention open question.
- Step 2 (Publish): the relay now holds its row lock from the claim through broker confirmation and the published_at update, so two relay instances cannot publish the same row (Q12).
- Step 2: the relay cycle is stated as every 5 seconds, matching the old worker (Q14).
- Step 3 (Accept): listed the fields of a new jobs row and how the sender finds due jobs, and stated that created_at is copied from the message (Q13, Q18).
- Step 3: the monolith's created_at now travels in the message and is stored as the job's created_at, so both sides count a day the same way (Q18).
- Step 4 (Send): split the claim into a short transaction, then a send with no open transaction; the lease is the only protection during the send; the lease length is now stated as a rule with the number left open (Q15).
- Step 4: a template render error in the service now counts as a failed attempt, so it cannot loop without ever reaching failed (Q16). This is a plan change.
- Step 6 (Record): an event for an unknown id or a monolith row is acked and dropped (Q17).
- Rollback step 3: stated that already-published service rows wait in the broker or the jobs table, and noted that the owner of the restore is open (Q19).
- Added terms for acknowledge and row lock, and rewrote the sweeper checks by name instead of by number.
- Split the document into 'How it runs' and 'How we roll it out', and moved the old-worker note into the flow.
- Merged the failure list into one table and added rows for render errors and relay crashes.
- Open questions: added the relay confirmation timeout, the lease length, a missing daily summary, the 02:00 UTC grace period, and the owner of the service restore.
- Rewrote the whole plan once for a newcomer, keeping the same fixed constraints, the same nine rollout steps in the same order, the same failure cases, the runbook, the rollback procedure and every open question.
- Added a short opening paragraph that says how notifications are sent today before saying how the new design changes that.
- Defined every term a newcomer needs in one plain line, including the idempotency key, row lock, lease, ack, topic, test row and reconciliation.
- Merged the three sweeper checks into one section, and removed the duplicate sweeper description that was spread across the terms and the flow.
- Merged the flow's per-step detail into one list. Each step now says what starts it, what data moves, where state lives and what goes wrong.
- Added the decided change that a template render error counts as a failed attempt in the service, with the reason: without it a bad template loops forever and no attempt is counted.
- Added the decided rule that the relay holds the row lock through the broker confirmation wait, which is what keeps two relay instances from publishing the same row.
- Added the decided rule that the service stores the monolith's created_at, so both sides count a notification on the same UTC day.
- Added the decided rule that a retry writes no event, so the monolith row's attempts value is exact only at its final state.
- Added the decided rule that status consumer acks unknown ids and monolith rows, and why acking matters.
- Added the decided test-row method: an operator inserts route = service rows for shipping_update into a team test mailbox, skipped by reconciliation on both sides.
- Cut the repeated Step 6-to-8 detail where it said the same thing, keeping each cutover's start, data, state, clock and rollback as separate short items.
- Removed cross-references such as 'step 6' inside the failure table and terms, and replaced them with the names of the things they point to, except where the rollout order itself needs a reference.

### Holes
- Q19: A service row that was already published when someone flips the flag back to monolith: the plan says it finishes on the service. If the service is down for a long time, who acts on those rows, given rollback says service rows are never moved back? (author: The plan does not say who acts. Known: rows wait in the broker or in the service's jobs table, so nothing is lost. A row still pending 30 minutes after publish pages on-call through the stuck-event check. Rollback says service rows are never moved back, so the only fix the plan names is restoring the service. Who owns that restore is not stated. It is listed as an open question.)
