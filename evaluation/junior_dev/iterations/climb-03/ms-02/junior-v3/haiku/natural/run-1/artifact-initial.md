# Plan: extract notifications into a Notification Service

This plan ships in 10 steps. Steps 1 to 6 change nothing user-visible. Step 7 moves the first type, and steps 8 and 9 move the other two, each after its soak gate. Step 10 removes the old worker.

## Shared mechanics

These are referred to by the steps below.

**Ownership in the monolith.** The `notifications` table stays the first place a notification is recorded. Business code is unchanged, so `enqueue_notification(tx, ...)` still inserts the row in the caller's transaction. Three columns are added to that table:

- `owner`: `monolith` (default for every row, old and new) or `service`.
- `claim`: null, `worker` or `relay`, with `claim_until` as the lease expiry.

Every row is owned by exactly one side at a time. The monolith worker sends only `owner = monolith` rows whose type is routed to the monolith. The relay hands off only `owner = monolith` rows whose type is routed to the service. Both take a claim inside a transaction with `FOR UPDATE SKIP LOCKED`, and both filter on `status = 'pending'`. A claim whose lease has expired is claimable again.

**Route flags.** `notifications.route.<type>` is read with `flags.get` and is `monolith` or `service`. It defaults to `monolith`. Flags reach the monolith within 10 s, so a flip takes effect well inside a minute. The service has no flag reads. It accepts whatever the relay hands it.

**Service data.** The service has its own database and never touches the monolith database. Its tables are:

- `inbox`: `id` (primary key, equal to the notification id), `type`, `email`, `payload`, `source_created_at`, `state` (`received`, `sending`, `sent`, `failed`), `attempts`, `first_attempt_at`, `next_attempt_at`, `lease_until`, `last_error`, and timestamps. Rows are kept at least 7 days.
- `results_outbox`: a result (`sent` or `failed`, with attempts and time) that is published to the broker and marked published only after confirmation.

**Broker.** Two topics: `notifications.requested` (relay to service) and `notifications.results` (service to monolith). Messages are keyed by notification id. The relay's message carries `{id, type, user_id, email, payload, created_at}`. The broker is the only channel between the two systems.

**Idempotency key.** Every MailRelay `send()` passes `idempotency_key = notification id`, from the old worker and from the service alike. Because both sides use the same key, a send made by one side is suppressed by MailRelay if the other side repeats it within 24 h.

**Retry policy, identical on both sides.** Up to 5 attempts. Backoff of 1, 2, 4 and 8 minutes before attempts 2 to 5. After attempt 5 fails, mark `failed` and page on-call. All retries fall inside the 24 h key window because their total span is about 15 minutes.

## Steps

### 1. Pass the notification id as the idempotency key on the old worker

- **Starts:** an ordinary deploy of `app/notifications.py`, with `idempotency_key=row.id` added to `mailrelay.send`.
- **Data moves:** none.
- **State:** unchanged. The monolith `notifications` table is the only store.
- **Failure:**
  - Crash after MailRelay accepts but before the batch commit: the rows stay `pending` and are re-sent on the next poll. MailRelay drops the repeat because the key matches and the send is within 24 h. This addresses the roughly 30 duplicates a week.
  - Crash in any other place, MailRelay down, or a timeout: the existing retry and backoff code applies unchanged.
  - Redelivery: not applicable to this step.
- **Note:** the per-batch commit is still there. Its duplicate risk is neutralised within 24 h but not fixed. That is acceptable for this step.
- **Gate to step 2:** one week of duplicate-email support tickets measured against the baseline of about 30 per week.

### 2. Add ownership, claims and route flags to the monolith with no behaviour change

- **Starts:** an additive migration and a deploy of the new worker.
- **Data moves:** none.
- **State:** `owner` (default `monolith`), `claim`, `claim_until` on `notifications`. Flags `notifications.route.<type>`, all `monolith`. The worker takes claims as described under Shared mechanics.
- **Failure:**
  - Flag read error: the worker sends nothing for flagged types during that loop and retries next loop. It never sends a `service`-owned row, because ownership is per row.
  - Crash during a claim: the lease expires and the row returns to the pool. Any repeat send carries the same key.
  - Migration: nullable or defaulted columns only, so there is no table rewrite.

### 3. Build the Notification Service with its own database and deploy it with no traffic

- **Starts:** the service is deployed to its own environment with its own database. No relay is pointed at it yet.
- **Data moves:** none yet.
- **State:** the `inbox` and `results_outbox` tables above.
- **Templates:** `templates.render` moves into the service. Both codebases use the same versioned template package, so they cannot drift until decommission. Golden-output tests compare the service's rendering with the monolith's for all three types.
- **Components:**
  - Consumer: validates the message, inserts it into `inbox` with `ON CONFLICT DO NOTHING`, commits, then acks. It does no sending, so the 30 s ack timeout is not at risk.
  - Sender: loops over claimable rows (state `received` or `sending`, `next_attempt_at <= now()`, lease null or expired) using `SKIP LOCKED`.
- **Sender rules:**
  - Claim, in one transaction: if `attempts >= 5`, mark `failed`, write a result, and page. Otherwise increment `attempts`, set `state = sending`, set `lease_until = now() + 60 s`, and set `first_attempt_at` if it is null.
  - Refuse any attempt more than 12 h after `first_attempt_at`. Mark `failed` and page instead. This keeps every send inside the 24 h key window with margin.
  - Send with `idempotency_key = id`. On success, mark `sent` and write a result, in one transaction.
  - On `mailrelay.Error` (including timeouts), if `attempts >= 5` mark `failed` and page. Otherwise set state to `received` and `next_attempt_at = now() + BACKOFF[attempts-1]` minutes.
- **Failure:**
  - Consumer crashes before ack: the broker redelivers. The insert conflicts with the existing row, so nothing changes and the message is acked.
  - Duplicate message after a terminal state: a no-op, and the message is acked.
  - Crash during a send: the lease expires and a retry goes out with the same key. If MailRelay had already accepted, the repeat is dropped and counts as success.
  - Crash after acceptance but before `sent` is committed: the same path as above. The row ends `sent` with no second email.
  - MailRelay down: backoff, then `failed` and a page after attempt 5.
  - Broker down: nothing is consumed and nothing is sent. Messages wait in the broker, which depends on the retention assumption in the open questions.
  - Results publish fails: the outbox keeps the row unpublished and retries until confirmed.
- **Deliberate change:** a crash now uses up an attempt, because the claim increments `attempts`. This prevents a poison message from looping forever. Today a crash does not count. This is listed as an open decision.
- **Gate to step 4:** golden-output parity for all three types, and passing fault tests with a fake MailRelay and a fake broker.

### 4. Add the handoff relay and the broker topics to the monolith, with no type routed

- **Starts:** deploy the relay thread and create `notifications.requested` and `notifications.results`.
- **Data moves:** none while every route is `monolith`.
- **Relay loop (about every 1 s):** claim up to a batch of rows where `owner = monolith`, `status = pending`, the type's route is `service`, and the claim is null or expired (`claim = relay`). Publish each row. Wait for the broker's confirmation. Then set `owner = service` and clear the claim.
- **Failure:**
  - Relay crashes after publish but before the owner update: the lease expires and the row is handed off again. The service inbox dedupes by id. If the monolith worker later reclaims the row (after a rollback), the cross-side repeat is suppressed by MailRelay's key within 24 h, because the lease is minutes long.
  - Broker down or confirmation timeout: the rows keep `owner = monolith` and simply wait. They are delayed, not lost. A confirmation timeout is ambiguous, so the relay republishes and the inbox dedupes. If the outage exceeds the threshold set in the open questions, roll the type's flag back.
  - Flag read error: the relay pauses.

### 5. Consume results in the monolith so `notifications.status` tracks the service

- **Starts:** deploy the consumer on `notifications.results`.
- **Data moves:** a result `{id, outcome: sent | failed, attempts, at}` flows from the service to the monolith.
- **State:** the monolith updates `status` only forward, with `UPDATE ... WHERE id = $1 AND status = 'pending'`. Terminal states never change.
- **Failure:**
  - Redelivery: the conditional update matches nothing and the message is acked.
  - Crash before ack: redelivery, as above.
  - Service down: `status` lags. Delivery is not affected.
- **Gate to step 6:** for a sample of test notifications, `status` matches what MailRelay accepted.

### 6. Rehearse cutover and rollback in staging

- **Starts:** a staging environment with the three types, MailRelay sandbox or test recipients, and a fake broker outage tool.
- **Scenarios to run:**
  - Flip a type to `service` while rows are pending, then flip it back.
  - Kill the relay mid-batch.
  - Kill the service mid-send.
  - Take the broker down for 10 minutes.
  - Make MailRelay return errors for a period.
- **Check:** zero duplicate recipient deliveries and zero lost notifications. Each rollback takes effect within a minute.
- **Gate to step 7:** every scenario passes, and the rollback procedure has been timed.

### 7. Move `shipping_update` (day 0)

- **Starts:** set `notifications.route.shipping_update = service`.
- **Data moves:** the relay claims the pending `shipping_update` backlog and all new rows of this type. The monolith worker stops claiming this type within 10 s. Claims in flight at the flip finish or expire. The claim rules prevent a double send.
- **State:** `owner` and `status` in the monolith; `inbox` and `results_outbox` in the service.
- **Failure:** the same cases as steps 3, 4 and 5. For a broker or service problem, flip the flag back to `monolith`.
- **Rollback:** flip back to `monolith`. The relay stops claiming new rows within 10 s, and the monolith worker resumes claiming unclaimed `shipping_update` rows. Rows the service already owns keep going in the service until they reach a terminal state. They are neither re-sent nor dropped.
- **Gate to step 8:** at least 3 days on the service, with zero duplicates reported, a failed count under the threshold (every failure paged), no `owner = service` row pending longer than the backlog threshold, and latency reviewed.

### 8. Move `order_confirmed` (day 3 or later)

- **Starts:** set `notifications.route.order_confirmed = service`.
- **Data moves, state, failure, rollback:** as step 7.
- **Measurement:** start recording enqueue-to-MailRelay latency now. It is `sent_at` on the service minus `created_at` from the message, which the monolith sets. Relay polling and broker transit are included, so measure them. Check clock skew between the monolith database and the service.
- **Gate to step 9:** at least 3 days on the service, the step 7 gate criteria, and p99 enqueue-to-MailRelay under 60 s on `order_confirmed`. Do not move `password_reset` until this p99 gate is met.

### 9. Move `password_reset` (day 6 or later, and only after the p99 gate)

- **Starts:** set `notifications.route.password_reset = service`.
- **Data moves, state, failure, rollback:** as step 7. The relay poll interval stays at about 1 s so the latency budget holds. The type is time-sensitive, so watch it closely.
- **Gate to step 10:** `password_reset` has run on the service for at least 7 days with the same criteria. The old worker stays deployable and remains a rollback path for this type throughout.

### 10. Hold for 7 days, then decommission the old worker

- **Starts:** `password_reset` has run on the service for 7 days (day 13 at the earliest).
- **Precondition:** zero `owner = monolith` rows with `status = pending` for 24 h. Confirm this query before removing anything.
- **Remove:** `run_worker`, `_deliver`, the monolith's copy of the templates, and the monolith's send path. Keep `enqueue_notification`, the `notifications` table, the relay and the results consumer. The relay is still needed because callers still record in the monolith. After this step there is no rollback to the monolith.
- **Failure:** if a `monolith`-owned pending row turns up after removal, the relay still routes it to the service, so nothing is lost. Investigate before reverting.

## Timeline (earliest)

| Day | Event |
|---|---|
| 0 | `shipping_update` moves |
| 3 | `order_confirmed` moves, after the `shipping_update` gate |
| 6 | `password_reset` moves, after the `order_confirmed` p99 gate |
| 13 | Old worker removed, after 7 days on `password_reset` |

Steps 1 to 6 come first. Each soak can run longer than its minimum.

## Open questions and assumptions

1. **Broker retention.** The plan assumes at least 7 days of retention, so inbox dedupe covers redeliveries. If retention is shorter, the inbox has to be kept longer, or redelivery beyond the window has to be treated as failed and paged.
2. **MailRelay key window.** Confirm whether the 24 h window is fixed from the first accepted send or sliding, and confirm that a key-dropped send is distinguishable from a fresh send. The plan treats both as success, as the overview describes.
3. **Crash attempts count.** Counting crashed attempts toward the 5 attempts differs from today's behaviour. Confirm this is acceptable, or change the claim to count only completed attempts.
4. **Email addresses on the broker.** Confirm with security and data owners that the broker may carry email addresses and payloads.
5. **Thresholds to set before step 7.** The failed-rate threshold, the maximum backlog age for `owner = service` rows, and the broker-outage duration that triggers rollback.
6. **Template drift.** Decide whether the shared template package is versioned and pinned, or released in lockstep with both deployables.
7. **Clock skew.** Confirm that the database and service clocks are synchronised within a bound small enough for the p99 gate.
8. **Relay versus change-data capture.** The plan uses polling from the monolith. CDC would also work, but it adds infrastructure and is not needed to meet the latency gate.