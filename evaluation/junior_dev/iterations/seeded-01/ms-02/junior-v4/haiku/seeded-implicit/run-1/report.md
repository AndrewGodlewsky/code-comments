## Review of ms-02 (junior-v4, author haiku, seeded-implicit)

Rounds: 5. Ended: teachback-correct.

### What changed
- Added the route column rule: route is set once at enqueue time from the flag, so each row has exactly one sender. The old plan left this vague.
- Added the published_at column and the outbox relay rules, including what happens if the relay crashes after publishing.
- Stated the message contents and that the service never calls back to the monolith.
- Defined the deliveries table, its primary key, and the insert-on-conflict dedupe. Acknowledgement happens before retries, so retries never depend on the 30-second ack window.
- Added the result path (notifications.result and the monolith result consumer), so the monolith row shows the final status.
- Added the cutover gates from the brief: 3 days per type, p99 under 60 seconds before password_reset, and 7 days before the old worker is removed.
- Added a rollback section that explains why a flag flip neither loses nor re-sends rows.
- Added the retry policy, kept identical to today's.
- Split the file into how it works, terms, rollout steps, rollback, retries and open questions, and removed the duplicate notes at the end of the old plan.
- Added an open question about broker redelivery after 24 hours, which is the limit of the MailRelay key.
- The file grew well past 1.5 times its first length. The brief requires data, state and failure detail for every step, so the extra length is needed, but the failure notes are not repeated in a second table.
- Main flow: rewrote as five numbered steps with what starts each one. The sender now polls deliveries every 5 seconds (Q10), and it publishes the result before it sets the deliveries row to sent or failed (Q11, Q12). The plan did not state this order before; the reverse order would lose a result on a crash between the two writes.
- Added the rule that the service consumer acknowledges only after its insert commits, and that the monolith result consumer acknowledges only after its update commits (Q14).
- Stated that intermediate failures publish nothing, and what the monolith row shows until the final result (Q15).
- Stated that the service keeps its own copy of the three templates, keyed by type (Q13).
- Added one failure table covering each step, including sender crash after MailRelay accepts, result publish failure, result consumer failure, and service down (Q12, Q14). Steps 3 to 7 point to the table instead of repeating failure notes, which merges the repeated text in steps 5 to 7 into one reference.
- Retries: stated which side pages on-call for each route, and where attempts and next_attempt_at are stored for each route.
- Open questions: added that a result-publish outage longer than 24 hours carries the same duplicate risk as a redelivery after 24 hours.
- Terms, Flag: now says the monolith reads it with flags.get(name) and that a change reaches every instance within 10 seconds (Q20).
- Main flow step 2: every monolith instance runs the relay, and a duplicate publish is safe because the service ignores the second copy (Q16).
- Main flow step 4: senders take rows with FOR UPDATE SKIP LOCKED, so several senders can run without taking the same row (Q17).
- Main flow steps 4 and 5: the result message carries the notification id, status and attempts, and the consumer updates the row by id (Q18).
- Main flow step 4: the attempt update is written right after a rejection, and the crash case before that write is stated (Q19).
- Failure table: added rows for two monolith instances publishing the same row, and for a sender crash between a MailRelay rejection and the attempt update (Q16, Q19).
- Main flow: each step now states what starts it, what it does, where its state lives and what happens on failure, in one shared layout.
- Step 2 (publish): the message now carries created_at, so the service can measure latency without reading the monolith database (Q28).
- Step 3 (store): deliveries stores created_at (Q28).
- Step 4 (send): each batch is one transaction, with locks held until it commits, so the lock behaviour is explicit (Q21).
- Step 4 (send): the retry wait is set from the retry schedule, which states the formula once (Q22).
- Step 4 and failure table: a result publish that fails is retried every poll with no limit, and attempts are not counted (Q23).
- Step 4 and failure table: a crash after paging may page on-call again; paging is kept before the row change so a page is never lost (Q24).
- Step 5 (copy back): a result is applied only while the row is pending on route service; otherwise it is logged and acknowledged, and repeats change nothing (Q25).
- Failure table: removed the flag-read row, which step 1 already covers, and rollout step 2 now refers to step 1 instead of repeating it (Q27).
- Rollout step 7: defined the p99 latency as accept time minus created_at over the 3-day order_confirmed run (Q28).
- Rollout steps 6 and 7: replaced repeated failure text with a reference to step 5.
- Retries: states the wait per attempt once, and confirms the old worker keeps its logic and poll for monolith rows (Q26).
- Open questions: added how long a flag read can take (Q27) and whether host clocks agree closely enough for the latency check (Q28).
- Step 4 (Send): added a bullet for template render errors, handled as a failed attempt for that row only, so the batch continues.
- Step 4 (Send): added a bullet for other unexpected errors, stating that the batch rolls back, sent rows return to pending, and the same key makes the resend safe.
- Failure table: added a row for a template render failure.
- Failure table: added a row for an unexpected batch error (rollback and resend with the same key).
- Retries: a template render error now counts as a failure, alongside a MailRelay timeout.
- Merged the retry rules, which appeared in three places (a Retries section, the steps and the failure table), into one 'Retry schedule' term. The steps and the failure table now refer to that term.
- Cut the separate 'Main flow after the move' intro, which repeated the step format.
- Gave every main-flow step the same four parts: what starts it, what it does, where its data lives, and what happens when it fails.
- Merged the two duplicate-publish failure rows (relay crash and two instances publishing the same row) into one row.
- Split the rollout (how we ship) from the main flow and rollback (how the system runs), and removed the rollout's repeated failure notes, which pointed back to the main flow.
- Corrected the claim that published results are harmless after a batch rollback. It holds for `sent` results only. Added an open question about `failed` results. Flagged, not changed: the plan's behavior is the same.
- Kept all fixed requirements, gates, timings, retry numbers and rollback rules from the brief and the original plan. Nothing was dropped from the plan's behavior.

### Holes
- None.
