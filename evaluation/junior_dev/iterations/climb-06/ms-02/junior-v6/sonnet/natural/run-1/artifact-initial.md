# Plan: extract notifications into a Notification Service

## Design the steps rely on

**Who owns a notification.** Each row in the monolith `notifications` table has exactly one owner at a time:

- `pending` is monolith-owned, and the old worker may send it.
- `forwarded` is service-owned. Once the broker has confirmed storing the message, the monolith never sends that row. The service sends it and reports the result back.
- `sent` and `failed` are terminal.

A row moves from `pending` to `forwarded` only inside a monolith transaction that holds the row lock (`FOR UPDATE SKIP LOCKED`). The old worker takes the same lock. So the old worker and the forwarder can never both act on one row, even while a 10 s flag change is still spreading across instances.

**Idempotency key as the backstop.** Every send, from either side, passes `idempotency_key = notification id`. MailRelay drops a second send with the same key within 24 h and returns success. A retry after a lost MailRelay response, a crash before commit, a redelivered broker message and a stale flag all collapse into one email within that window.

**Service-side dedupe.** The service keeps its own `notifications` table with the notification id as primary key. It keeps rows for at least 30 days, which is longer than MailRelay's 24 h key window. A redelivered or republished message for a known id never re-sends.

**Routing.** There is one flag per type: `notif.route.<type>` with values `monolith` or `service`. It defaults to `monolith`. Only the monolith reads it. The service never needs the flag, because it finishes whatever it has received.

**Message contract.**

- `notifications.requested` carries `id, type, user_id, email, payload, created_at, attempts, next_attempt_at`. It carries `attempts` and `next_attempt_at` so retry state survives a handoff.
- `notifications.result` carries `id, outcome (sent|failed), attempts`.

**Retry policy in the service.**

- It is identical to today's: 5 attempts, waits of 1, 2, 4 and 8 minutes, then `failed` plus a page.
- Each row is processed in its own transaction, not one commit per batch.
- A render exception counts as a failed attempt under the same policy. Today it would roll back the whole batch and loop forever.

## Steps

### 1. Pass the idempotency key from the old worker

- **Starts:** a normal monolith deploy. This is the first change shipped. No type has moved yet.
- **Change:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`.
- **Data moves:** none. Only the MailRelay call changes.
- **State:** unchanged. The `notifications` table is the only state.
- **Failure behaviour:**
  - A crash after MailRelay accepts but before the batch commit leaves rows `pending`. They are resent with the same key, and MailRelay drops the duplicate and returns success. This fixes the roughly 30 duplicate emails a week.
  - A timeout where MailRelay actually accepted the send also collapses to one email on retry.
  - The longest retry window is 15 minutes, well inside the 24 h key lifetime.
  - During the rolling deploy, instances without the key behave as today. Duplicates fall as the rollout completes.
- **Exit check:** a week of support duplicate reports drops to about zero. Confirm with MailRelay that the key behaviour is as documented.

### 2. Build the service, still unused by production traffic

- **Starts:** a deploy of the new service. Nothing in the monolith has changed yet.
- **Data moves:** none in production. Templates are copied into the service. Freeze template edits, or apply them to both copies, until decommission.
- **State:** a new service database with a `notifications` table. It has `id` as primary key, type, email, payload, status (`pending|sent|failed`), attempts, `next_attempt_at`, `paged_at`, and timestamps.
- **Components:**
  - **Consumer.** In one service-DB transaction it runs `INSERT ... ON CONFLICT (id) DO NOTHING`, then acks the message. A crash before commit means no ack and the broker redelivers. A crash after commit but before ack means redelivery, a conflict, a no-op, and an ack. The insert is fast, so the 30 s ack deadline is not a concern.
  - **Sender loop.**
    - It claims one due row with `FOR UPDATE SKIP LOCKED`, renders, sends with the key, updates the row and commits.
    - On a crash mid-send the lock is released. The row is retried with the same key, which MailRelay drops if the first send was accepted.
    - A failed send is handled as today. Attempts 1 to 4 set `next_attempt_at` to now plus 1, 2, 4 or 8 minutes. Attempt 5 sets `failed`.
  - **Result publisher.** After the terminal state is committed, it publishes the `sent` or `failed` result. A result that is never published is recovered in step 3.
  - **Pager.** A separate loop pages on-call for rows that are `failed` with `paged_at IS NULL`, then sets `paged_at`. Paging is not part of the send transaction, so an alerting outage cannot cause a sixth MailRelay attempt, and a failure is never left unpaged. A duplicate page after a crash is acceptable.
- **Failure behaviour:**
  - MailRelay down: rows retry on the policy, then fail and page.
  - Broker down: the consumer stops receiving. The sender keeps working on rows already stored. Result messages queue in a small service-side retry loop. The service stores them in the `notifications` table via a `result_published` flag, so a restart resends them.
  - Redelivered message: no-op, as described above.
- **Exit check, in staging against a MailRelay sandbox or a stub that honours `idempotency_key`:**
  - Fault injection: kill the consumer after insert and before ack, kill the sender after the stub accepts and before commit, take the stub down for more than 15 minutes, and take the broker down.
  - Render parity: for every stored payload of the three types, the service output matches `templates.render` in the monolith byte for byte.
  - Assertion: each notification id produces exactly one accepted send.

### 3. Add the monolith side, dark

- **Starts:** a monolith deploy. All three flags are `monolith`, so behaviour does not change.
- **Changes:**
  - Add the `forwarded` status. No schema change is strictly needed, because the old worker selects only `pending`.
  - Old worker: add `AND type NOT IN (service-routed types)`. It reads the flags when it starts each batch.
  - **Forwarder thread** (polls every 1 s):
    - It selects `pending` rows of service-routed types `FOR UPDATE SKIP LOCKED`, regardless of `next_attempt_at`. It re-checks the flag after taking the lock.
    - It publishes the message to `notifications.requested` and waits for the broker confirmation.
    - It sets `status='forwarded'` and commits.
    - It holds no CPU-heavy work. It does no rendering and no MailRelay call.
  - **Result consumer:** it applies `UPDATE ... WHERE id=? AND status='forwarded'`. If the row is already terminal, it acks as a no-op. If the row is still `pending`, it does not ack, and redelivery 30 s later retries. That covers a result that arrives before the forwarder commits.
  - **Reconciler:** every 10 minutes it finds `forwarded` rows older than 1 hour with no result. It republishes them and raises an alert. Republishing is safe because the service dedupes by id, and the service republishes its stored terminal result for a known id.
- **State:** the monolith `notifications` table remains the first record. The service DB holds service-owned state. The two sides communicate only via the broker.
- **Failure behaviour:**
  - Crash after the broker confirms but before the commit: the row stays `pending` and is republished. The service dedupes.
  - Broker down: publishing fails, rows stay `pending`, and the forwarder retries each poll. Alert when the oldest forwardable row is older than 2 minutes. Nothing is lost.
  - Lost confirmation: the row is treated as unpublished and republished. This is the one case that is ambiguous, and it matters in the residual risks below.
- **Gate:** every monolith instance must run this version before any flag changes. Otherwise a stale old worker could ignore the filter. Check build versions on all instances.

### 4. Move `shipping_update`

- **Starts:** flip `notif.route.shipping_update=service`. It reaches all instances within 10 s.
- **Data moves:**
  - New carrier-webhook notifications are inserted by `enqueue_notification` exactly as today.
  - The forwarder publishes each row, including any `pending` rows with existing retry state (`attempts`, `next_attempt_at`). Those keep their remaining attempts, so retries are not reset.
  - The service sends them and returns results.
- **State:**
  - Before the broker confirms, the row is `pending` in the monolith.
  - After the confirm, ownership passes to the service DB.
  - Terminal status is mirrored back to the monolith row.
- **Failure behaviour:**
  - A row the old worker has locked at the moment of the flip stays with it until the batch commits. If it fails and is scheduled for retry, the row is `pending` again and the forwarder takes it on the next poll.
  - A stale instance within the 10 s window cannot double-send, because of the row lock and status.
  - Everything else is as in steps 2 and 3.
- **Soak:** at least 3 days, with these checks.
  - Counts reconcile: rows forwarded equals rows inserted in the service equals results received.
  - The number of `forwarded` rows older than 1 hour is 0.
  - Duplicate-email reports are 0.
  - Failed rows are all paged.
  - Monolith CPU and DB connection use have dropped.
- **Rollback drill on day 1:**
  1. Flip to `monolith`.
  2. Confirm new rows are sent by the old worker.
  3. Confirm rows already forwarded are still completed by the service, because the service keeps consuming and sending.
  4. Confirm no row is sent twice.
  5. Flip back to `service`.
  - The 3-day clock starts after the last flip back.
  - To roll back, flip the flag. It takes effect in at most 10 s, which is inside the one-minute limit. Rows already forwarded stay with the service and are never picked up by the old worker. Rows not yet forwarded go to the old worker. In-flight rows are neither lost nor re-sent.

### 5. Move `order_confirmed`

- **Starts:** flip `notif.route.order_confirmed=service`, only after `shipping_update` has run on the service for 3 or more days with the checks above clean.
- **Data, state and failures:** same as step 4. The volume is 12,000 a day, roughly 0.14 a second, so capacity is not a concern.
- **Added measurement:** record p99 enqueue-to-MailRelay latency. It runs from the row's `created_at` to MailRelay accepting the send. The service stores the accept time and emits it with the result. Break the figure down by stage: forwarder wait, broker, service queue, send.
  - A first-attempt MailRelay failure adds at least 1 minute. The 60 s requirement therefore holds only if first-attempt failures are well under 1%. Track that rate separately from service-caused latency.
- **Soak:** at least 3 days.
- **Rollback:** as in step 4.

### 6. Move `password_reset`

- **Starts:** flip `notif.route.password_reset=service`, only when both conditions hold.
  1. `order_confirmed` has run on the service for 3 or more days.
  2. Measured p99 enqueue-to-MailRelay latency on `order_confirmed` is under 60 s over that period.
- **Data, state and failures:** same as step 5.
- **Extra safeguards:**
  - Alert when the p99 latency of `password_reset` exceeds 45 s over 15 minutes.
  - Alert when the oldest `pending` or `forwarded` `password_reset` row is older than 30 s.
  - If p99 breaches 60 s and the cause is the service path, flip back at once.
- **Soak:** keep the old worker deployed and the flags in place for 7 days.

### 7. Decommission the old worker

- **Starts:** 7 days after step 6, with no rollback during that time and the step 5 and 6 checks clean.
- **Pre-checks:**
  - There are zero `pending` rows owned by the monolith.
  - There are zero `forwarded` rows older than 1 hour.
  - The reconciler is quiet.
- **Changes, in order:**
  1. Remove `run_worker`, `_deliver` and the monolith template and MailRelay code that nothing else uses.
  2. Make the forwarder forward every type unconditionally.
  3. Remove the three routing flags.
- **Kept:** `enqueue_notification`, the forwarder, the result consumer and the reconciler.
- **Failure behaviour:** after this step, rollback to monolith sending is a code revert, not a flag flip. That is expected.
- **Mixed deploy:** during the rolling deploy, instances that still run the old worker also honour the flags, which all say `service`, so no instance sends mail itself.

## Residual risks to review

- **24 h key window.** If a send is accepted and the service then stays down for more than 24 h before the row is retried, MailRelay's key has expired and the retry could duplicate. This is limited to the one row each instance has in progress. Alert when the service backlog ages past 1 hour.
- **Ambiguous broker confirm combined with rollback.** The forwarder publishes, the confirmation is lost, the row stays `pending`, and the flag is then flipped to `monolith`. Both the old worker and the service can then send. Only the idempotency key prevents a duplicate, so this is safe only within 24 h. Runbook rule: if a broker outage has lasted more than 12 h, involve a human before flipping any flag back.
- **Staging fidelity.** Step 2 assumes a MailRelay sandbox or a stub that mimics the key behaviour. Confirm which one exists before starting.
