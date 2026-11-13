## Review of ms-02 (junior-v4, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a 'How it works today' section that explains the old worker, its 5-second loop, and the batch commit that causes the duplicates (Q1).
- Stated the service consumer's insert values: `pending` for live rows with `next_attempt_at = now()`, and `shadow` for shadow rows (Q2).
- Named the outbox publisher and the new `notification-events` topic, and said that the completion consumer reads it (Q3).
- Moved the service outbox publisher and the monolith completion consumer from step 5 into step 4, since shadow reports need them. Step 5 now holds only the reconciler (ordering fix).
- Defined the 5-second service poll and added the lease condition to the claim query, so that two instances cannot claim the same row (Q4).
- Added to the consumer: on a redelivery of a terminal row, re-emit the completion event. The reconciler and lost-event recovery depend on this, and the earlier text did not have it (Q5).
- Reworded the reconciler: a republish to a row the service is still retrying does nothing, and the republish restarts the 30-minute timer. The 23-hour fail rule now fires only after repeated republishes (Q5).
- Defined shadow sampling (2 percent, deterministic by id), added the `shadow_sampled` and `shadow_render_hash` columns, and defined render_hash. Both sides compare when the second write lands (Q6).
- Defined the route flag name and when it is read (Q7).
- Merged the attempt rules into one check before each send and one rule after an error. Stated the maximum of 5 sends and marked the crash-counts-as-attempt change as a decision (Q8).
- Added to the old worker's step 2 that it writes render_hash and compares it with shadow_render_hash, and added a step 2 gate for the route filter.
- Added open question 9 (service instance count, unknown) and noted in open question 1 that a lease expiry relies on MailRelay dropping a repeated key.
- Restructured the file into summary, terms, today, rules, data, service algorithm, and rollout steps, each with the same four parts (starts, data moves, state, failures) and a gate. Moved the invariants into 'Rules the plan keeps' and the created_at note into Terms.
- Cut repeated failure text in steps 7 and 8, which now refer to step 6's pattern in full rather than restating it, and cut the separate failure restatements in the design sections.
- Service algorithm, step 2: says the customer gets no email on a failed row, and that on-call checks MailRelay by key and notes the result, with the monolith row staying failed.
- Service algorithm, step 3: the MailRelay call timeout is kept well under the 2-minute lease.
- Service algorithm, steps 4 and 5: the success write applies while the row is pending, and the error writes apply only while the worker still holds its claimed lease. This covers a lease that expires mid-send.
- Service algorithm, after step 5: a lease that expires during a send lets a second worker claim the row. The same key should make MailRelay drop that send, and the limit of 5 sends per row still holds.
- Data: render_hash is written by the old worker at send time, in the same UPDATE as the outcome. A new Shadow comparison paragraph states which side compares and alerts, and what happens if the shadow report arrives first.
- Monolith completion consumer: the completion UPDATE states the status mapping (sent to sent, failed to failed) and that a repeat or late event matches no row, changes nothing and is acknowledged. The shadow report update points to the Shadow comparison paragraph.
- Step 2, changes: replaces the unclear shadow_render_hash wording with the UPDATE ... RETURNING comparison in plain words.
- Step 3, starts and data moves: the publisher claims route = 'service' rows (live) and route = 'monolith' AND shadow_sampled rows (shadow, only while the shadow switch is on). Each id gets one message kind. The gate now says zero messages while the shadow switch is off.
- Step 4, starts and gate: the shadow switch is named as the trigger. The parity gate counts only rows that have both hashes.
- Open questions: added question 10 on whether an outcome-unknown row should be corrected to sent. The brief does not require this, but the monolith status can be wrong without it. Other questions are unchanged. The file is about 15 percent longer than before.
- Merged the 'How it works today' bullets into a two-sentence paragraph in the summary.
- Removed the separate 'Rules the plan keeps' list. Its points now sit in the summary, the route term, the inbox step and the send rules.
- Shortened the terms to one line each, in plain words. Added the 'shadow switch' term, which the text used without defining.
- Merged the inbox consumer, the outbox publishers and the completion consumer into numbered steps 4 to 6. Each step now has the same parts: starts, does, data, failures.
- Merged the duplicate send-algorithm rules and the failure bullets into one service sender step, with the retry policy in its own paragraph.
- Moved the monolith failure cases into a short summary table. Cross-cutting failures are listed once, at the step where they occur.
- Separated how the system runs from how it is rolled out, with its own heading. Rollout steps 1 to 9 keep the same parts in the same order.
- Replaced references such as 'open question 1' with the question's topic, so the reader is not sent to a number.
- Cut the repeated per-step wording in the rollout: 'the same as step 6' is kept, and repeated failure lists are dropped where they duplicated the system steps.
- Simplified the shadow comparison into one paragraph. The mechanics and the rule that only rows with both hashes count are unchanged.
- Kept the timeline table, and kept the retention, topic and schema details under Data.
- Added open question 11 to flag that counting a crash as an attempt departs from the brief's 'keep today's policy exactly'. The plan's behaviour is unchanged. This is the only addition, and it records a conflict the original plan already noted but did not list for sign-off.

### Holes
- None.
