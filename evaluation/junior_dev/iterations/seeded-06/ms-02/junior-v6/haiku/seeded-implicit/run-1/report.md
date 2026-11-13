## Review of ms-02 (junior-v6, author haiku, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Rewrote the plan into four parts: summary and terms, how it runs per step, what happens when things fail, and the rollout steps with gates. The first version lacked the per-step start, data, state and failure detail the brief asks for.
- Defined route as set once at enqueue from notify.route.<type>, and made the old worker pick only route monolith rows (Q3, Q7).
- Added the published_at column and the outbox relay design: a poll, FOR UPDATE SKIP LOCKED, and publish-then-mark (Q2).
- Made the service's deliveries table and its retries follow today's 5-attempt, 1/2/4/8-minute policy, with the page on the fifth failure (Q5).
- Stated the two dedupe layers: the deliveries primary key for broker and relay duplicates, and the MailRelay idempotency key for crashes after send (Q6).
- Added the rollback rule: rows keep their route, the relay and service keep draining, and each row has one sender (Q7).
- Added created_at to the message contract so latency can be measured from enqueue (Q8).
- Put the cutover gates from the brief into the rollout steps: 3 days per type, p99 under 60 seconds on order_confirmed before password_reset, and 7 days before the old worker is removed.
- Kept the first version's notes on retries, dedupe, rollback, and watching backlog, failed counts and latency, and kept the brief's per-day volumes.
- Added the open questions: the latency window and clock, the monolith's need for final status, broker retention during rollback, the 24-hour MailRelay window, and whether the relay and flags stay after step 8.
- Restructured the document for a newcomer: a summary paragraph, terms defined in one line each, numbered steps that each stand alone, a failure table, rollback, a separate shipping section, and open questions. Removed the R- and Q-style codes.
- Step 4 now claims each row in a short committed transaction before the MailRelay call, counting the attempt and setting the next attempt time. Reason (Q12): a crash during a send must use up an attempt, or a row could be retried without end. Retry policy is unchanged: 5 attempts, backoff 1, 2, 4 and 8 minutes, then failed and paged.
- Step 4 now states the 5-second poll and 50-row batch, and says rows are locked with FOR UPDATE SKIP LOCKED during the claim (Q9, Q10).
- Step 5 now says render failures count as failed attempts, with the same policy (Q11). Previously the document was silent on this.
- Added a row to the failure table for a crash during attempt 5, which can page on-call for a send MailRelay accepted (Q12).
- Where the status lives now says plainly that the monolith row is not changed or removed after published_at, and that a failed service notification is visible only in the service's deliveries table and the page (Q13).
- Added an open question: who looks up the final status of a service notification for support, since the monolith row shows only published_at (Q13).
- Kept every requirement and number from the brief and the first version, including the 40,000, 12,000 and 1,500 daily volumes, the 30-second broker redelivery, the 10-second flag propagation, the 24-hour MailRelay key window, the 30 duplicate emails a week, and the 3-day, 7-day and 60-second gates.
- Step 2 (How it runs): the relay's lock span is now stated (read through batch commit, covering publish and confirmation), with the per-batch commit and the crash-republish case (Q15).
- Step 3: the consumer acknowledges after the insert commits in both the new-row and the no-op case (Q18).
- Step 4: the claim sets the next attempt time to now plus the backoff, and the MailRelay call must time out sooner than 1 minute (Q16).
- Step 5: on failure, the next attempt time is set to failure time plus backoff, as today's worker does (Q17).
- Old path: the old worker's render error now counts as a failed attempt, as the policy requires; today it escapes the batch (Q11 carry-over).
- Where the status lives: the monolith row's status stays pending for service rows and is not read (Q14).
- Terms: added Due, Attempt, Published, Backlog, Failed count, Enqueue-to-MailRelay latency; route is defined as the worker selector (Q14, Q19).
- Failure table: added the sent-write-fails case and the send-past-timeout case (Q16); the service-crash rows now refer to the claim as a guard.
- How we ship it: split from How it runs; each step names its gate, and step 2 sets the column default to monolith and bars flag flips before its gate (Q19, Q20).
- Step 8: states that removing the old worker ends flag-flip rollback for monolith rows, and adds this to the open questions (Q19).
- Open questions: added gate ownership and thresholds, post-step-8 rollback, and gates for steps 1 to 4 (Q19).
- Cut the question and answer references, the Changed notes and the review history. Every point they settled is now stated in plain words in the step where it applies.
- Added a short list of rules the plan must keep (no loss, no duplicates, idempotency key, retry policy, separate data), taken from the brief.
- Added terms that were missing: Monolith, MailRelay, Notification Service, Consumer, Sender, Acknowledge, On-call page. Defined Route, Flag and Claim in more detail. Each term is one line.
- Step 2 (Publish) now says the lock span, the per-batch commit, the crash case that republishes, and the broker-down case. Added that rows wait in the monolith and are delayed, not lost.
- Step 3 (Store) now says the consumer acknowledges after the commit in both cases, whether the row is new or already existed.
- Step 4 (Claim and send) is split into limit check, claim, and render and send. It says what time the claim sets after each attempt, and that the MailRelay timeout must be under 1 minute.
- Step 5 (Retry and fail) says the backoff counts from the failure time, and that render errors, MailRelay errors and timeouts all take this path.
- Step 6 (old path) says a render error counts as a failed attempt, and that the old worker still commits once per batch with the same keys.
- Added a Where the status lives step and a Rollback step, each in plain words, so the rollback is explained in the flow and not only in the table.
- Failure table: kept every case from the brief and the first draft, including crash, broker down, MailRelay down, redelivery, timeout and render failure. Reworded the rows to match the steps. Removed no case.
- Moved the rollout order and gates into a separate How we ship it section, apart from How it runs. Step 2 now says why no flag may be on before every instance runs the new code.
- Open questions: kept every open question from the draft. Added the question on whether the 24-hour MailRelay key window is enough if the sender is down longer.
- Kept the design, the numbers (5 attempts, 1/2/4/8 minute backoff, 5-second poll, 50-row batch, 10-second flag propagation, 30-second broker redelivery, 3-day and 7-day spans, p99 under 60 seconds, 40,000/12,000/1,500 daily volumes) and the step order unchanged.
- Length is about 2,300 words, within about one and a half times the first draft's length.
- Step 4: split the batch read from the claim. The read holds no lock; each claim locks its own row with FOR UPDATE SKIP LOCKED, rechecks it is still pending and due, and counts the attempt in the same transaction (Q21, Q22).
- Step 4: the attempt-5 claim now sets a 1-minute guard time, not now, so another instance cannot mark the row failed and page while the last send runs (Q21).
- Step 4: the MailRelay timeout is 45 seconds, so a timed-out send's failure write lands before the 1-minute guard expires (Q25).
- Steps 4 and 5: sent and failed writes apply only if the attempt count still equals the claimed count. A late failure write leaves the row due at its guard time (Q25).
- Step 4 and Terms: the sent write records accepted_at, and the deliveries table gains that field (Q23).
- Terms: Backlog is counted by the relay in the monolith; failed count is counted in the service (Q23).
- Failure table: a sent-write failure now gives the guard-time wait per attempt (1, 2, 4, 8 minutes); the attempt-5 crash case is due after 1 minute, not at once; a new row covers a late or failed failure write (Q21, Q24, Q25).
- Open questions: removed the question about how long the sender's row lock is held, because step 4 now decides it (Q22). Added a question on whether the 45-second timeout and 1-minute guard fit MailRelay's real latency.
- Whole file rewritten for a newcomer: added plain-language terms for guard time, claim and accepted_at; separated how it runs from the rollout; renamed the rollout steps Deploy 1 to Deploy 8 so they are not confused with run steps; merged repeated rules; kept every requirement and number from the brief and the first version (volumes, 24-hour key, 30-second redelivery, 10-second flag, 3-day and 7-day spans, 60-second p99, the 5-attempt and 1/2/4/8-minute policy).

### Holes
- Q8: What does 'latency looks good' mean for password_reset: which latency, measured where, and what is the threshold? (author: The brief fixes the metric and threshold: enqueue-to-MailRelay latency, p99 under 60 seconds, measured on order_confirmed. The service can measure it, because the message carries created_at and the service records the MailRelay accept time. Not known: the window length, whether retries count, and how the clock is synchronised across hosts. These are listed as open questions.)
- Q19: Step 8 says to keep the old worker deployable until then. What is the rollback path after step 8, and what must be true for the relay and flags to be removed? Also, who decides a step has 'passed its gate' and how is it checked? (author: Known: the gate criteria for steps 5 to 7 are the time spans and the latency check the brief gives, plus the three watched measures. Not known: who checks a gate, what counts as a bad backlog, failed count or latency (the brief gives no thresholds), and whether gates for steps 1 to 4 need more than running on every instance. Rollback after step 8 is also not known: removing the old worker means a flag flip can no longer send monolith rows, which conflicts with the brief's flag-flip rule. Whether the relay and flags stay after step 8 is not decided. All of these are in the open questions. Changed: each step names its gate, and step 8 says what removal does to rollback.)
