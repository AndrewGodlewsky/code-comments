## Review of ev-03 (junior, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Reordered the document to summary, terms, diagram, steps, state, failures, then open questions, as the brief and the skill require.
- Defined the hint's contents as the full message, so the client needs no body fetch (Q1).
- Replaced the undefined 'delayed job at hint time + 5 s' with one sweeper that runs every second in each fan-out worker, and added a hinted_at column to pending (Q2, Q4).
- Step 7b now sets push_sent_at, so an offline recipient is not pushed twice (Q3).
- Fixed a real gap: when presence is unavailable, the first version never set a hint time, so the 5-second step 8 check could not fire. Step 7c now sets hinted_at and sends no hint, which keeps the stated intent (Q4 and the failure table).
- A failed hint send now also falls back to the sweeper, so there is one fallback mechanism instead of two.
- Stated that the database assigns msg_id in the send transaction (Q5).
- Stated the one-device presence rule and moved the sender's other devices to open questions (Q6).
- Reconnect sync now joins bodies, sends pages, and ends with a sync-complete frame (Q7).
- Stated the relay is a separate process that polls every 500 ms and uses FOR UPDATE SKIP LOCKED (Q8).
- Assigned pending-row expiry to the sweeper, which the first version left unnamed.
- Folded the client ack into step 9 so it applies to both live and sync deliveries, and renumbered the diagram 1 to 11 to match.
- Kept every brief requirement and every failure case from the first version, and merged repeated wording such as the hint and sweeper rules.
- Terms: added a Topic term, and explained hinted_at inside the Pending row term.
- Step 2: added that the insert runs first so a retry never takes a seq, and that the conv_seq row lock is taken at the increment and held until commit.
- Step 4: added that the topic key is conv_id, and that live order is not guaranteed across relays or retries.
- Step 7 and diagram 7a and 7c: hinted_at is set only if it is NULL, so a failed hint after 7a does not reset the 5-second window.
- Step 8: added that the 5-second window catches both lost hints and late acks.
- Step 9: added that any gateway node can delete the pending row, because pending lives in the Message Store.
- Client state: defined a gap as a seq neither received nor sent by the client, and explained the history API fetch on a gap.
- Open questions: added unknowns for push while the app is open, the history API endpoint name, and clients that lost local state.
- Added one sentence at the top saying how the system works today (clients only see new messages on history reload), as the skill requires when a change touches an existing system.
- Merged the old Where state lives section into the Terms, so each store, field and identifier is defined once with its location and rules.
- Defined every term a newcomer would not know: WebSocket, heartbeat, TTL, key-value store, topic, row lock, ON CONFLICT DO NOTHING, FOR UPDATE SKIP LOCKED, idempotent, at-least-once, dedupe, read-after-write consistency, gap, sync, push provider.
- Defined the hint's contents (msg_id, conv_id, seq, sender, body) and its non-durable, in-memory nature in the Hint term and step 7a (Q1).
- Defined the sweeper as one timed job per worker running every second over pending rows, with no per-recipient job (Q2).
- Stated in step 7b that the push also sets push_sent_at, so an offline recipient gets one push (Q3); stated in 7a and 7c that hinted_at is set only if NULL, and that hinted_at is set once (Q9, Q15).
- Stated the relay as a separate process with a 500 ms timer and FOR UPDATE SKIP LOCKED (Q8), and the conv_id partition and ordering limits in step 4 (Q13).
- Stated the sender ack carries msg_id and seq, that the database assigns msg_id at insert, and that seq comes from the same-transaction increment (Q5). Added the insert-first reasoning and the second-sender wait at the conv_seq lock to step 2 (Q12).
- Stated in step 9 that the client ack may reach any gateway node, which deletes the row by user and msg_id (Q14); stated in step 11 that sync sends pages of 100 with bodies and a sync-complete frame (Q7).
- Moved each single-step failure from the old failure table into the step where it happens, so each failure is stated once. Cross-step failures stay in the step where they begin (the race in step 10, the reconnect interleave in step 11). Dropped the separate table, which repeated those rows.
- Kept every brief requirement and first-version fact: one device per user, 10 s heartbeat, 30 s offline rule, 200-member cap with sender excluded, ack after commit, error and same-id retry, 5 s ack window, 30-day retention, best-effort never-retried push, seq-ordered reconnect, at-least-once with dedupe, and the out-of-scope list. Kept the diagram unchanged, since it already shows the Q3, Q9 and Q15 rules.
- Did not add the Q10 rare ack-versus-sweeper race to the file, following the answer's own note. Did not change the plan's behaviour anywhere.
- Kept all first-version open questions and unknowns, including the push-while-app-open question, the history API endpoint name, the reinstall gap case and the broker retention value.

### Holes
- None.
