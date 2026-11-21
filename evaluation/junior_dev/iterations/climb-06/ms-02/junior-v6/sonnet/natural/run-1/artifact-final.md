# Plan: extract notifications into a Notification Service

## Summary

Today, notification sending runs inside the monolith and competes with checkout for CPU and database connections. Business code calls `enqueue_notification(tx, ...)` inside its own transaction (checkout, the carrier webhook, password reset). That inserts a `pending` row into the monolith `notifications` table, and the row exists only if the caller's transaction commits. A worker thread on every monolith instance polls every 5 s, locks up to 50 due `pending` rows (`FOR UPDATE SKIP LOCKED`), renders and sends each one, and commits once per batch. If an instance dies after MailRelay accepts some of a batch but before the commit, those rows are sent again. Support sees about 30 duplicate emails a week.

This plan moves rendering and sending into a separately deployed Notification Service with its own database. Callers do not change, and the monolith table is still the first place a notification is recorded. A forwarder in the monolith publishes each `pending` row of a moved type to the broker, which is the only channel between the two systems. The service stores the message, renders, sends through MailRelay, and publishes a result back. The monolith copies the result into its row. We move one type at a time behind a flag, so any type can go back with a flag flip. First, the old worker starts passing an idempotency key, so duplicates are stopped before anything moves.

Rules that hold throughout:

- Every notification whose enqueuing transaction committed ends up either accepted by MailRelay, or marked `failed` with on-call paged.
- A user never gets the same notification twice: not after a crash, broker redelivery, cutover or rollback.
- The service never reads or writes the monolith database, and the monolith never touches the service's.
- Retries keep today's policy exactly, on whichever side sends: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then mark `failed` and page on-call.

## Terms

- **MailRelay:** the external email service all three types send through. `send()` hands it one email. It returns success once it has accepted the send. If it has already accepted a send with the same `idempotency_key` in the last 24 h, it drops the new one and still returns success, so the caller cannot tell a duplicate from a first send. We pass no key today.
- **Broker:** the shared message broker (already used by billing and search). It is at-least-once: a message not acknowledged within 30 s is redelivered, possibly to a different consumer. After storing a published message, the broker sends the publisher a confirmation. The publisher waits for it.
- **Flag:** a runtime flag read with `flags.get(name)` in the monolith. A change reaches every monolith instance within 10 s.
- **Old worker:** today's `run_worker` and `_deliver` in `app/notifications.py`.
- **Forwarder:** a new monolith thread that publishes `pending` rows to the broker.
- **Types** (all email only):

| type | enqueued when | per day | requirement |
|---|---|---:|---|
| `shipping_update` | carrier webhook updates a shipment | 40,000 | none |
| `order_confirmed` | checkout commits an order | 12,000 | none |
| `password_reset` | a user asks to reset their password | 1,500 | p99 enqueue-to-MailRelay under 60 s |

## How the system runs (once built)

### Who owns a notification

Each row in the monolith `notifications` table has one owner at a time:

- `pending`: monolith-owned. The old worker may send it.
- `forwarded`: service-owned. Once the broker has confirmed storing the message, the monolith never sends that row. The service sends it and reports back.
- `sent` and `failed`: terminal.

A row moves from `pending` to `forwarded` only inside a monolith transaction that holds the row lock (`FOR UPDATE SKIP LOCKED`). The old worker takes the same lock, so the two can never both act on one row, even while a 10 s flag change is still spreading.

### Idempotency key and dedupe

- Every send, from either side, passes `idempotency_key = notification id`. A retry after a lost MailRelay response, a crash before commit, a redelivered message and a stale flag all collapse into one email within 24 h.
- The service keeps its own `notifications` table with the notification id as primary key, and keeps rows at least 30 days (longer than the 24 h key window). A redelivered or republished message for a known id never re-sends.

### Routing

One flag per type, `notif.route.<type>`, with values `monolith` or `service`, default `monolith`. Only the monolith reads it. The service never needs it, because it finishes whatever it has received.

### Messages

- `notifications.requested`: `id, type, user_id, email, payload, created_at, attempts, next_attempt_at`. The last two carry retry state across the handoff. The service stores both, and its sender sends the row only when `next_attempt_at` is due.
- `notifications.result`: `id, outcome (sent|failed), attempts`. The monolith copies `outcome` into `status` and `attempts` into its `attempts` column.

### Service parts

The service `notifications` table has: `id` (primary key), type, email, payload, status (`pending|sent|failed`), attempts, `next_attempt_at`, `created_at` (from the message), `accepted_at` (when MailRelay accepted the send, empty until then), `paged_at`, `result_published` (false until the result message is published), and other timestamps.

- **Consumer.** In one service-DB transaction: `INSERT ... ON CONFLICT (id) DO NOTHING`, copying `attempts` and `next_attempt_at`, then ack. Crash before commit: no ack, the broker redelivers. Crash after commit but before ack: redelivery, conflict, no-op, ack. The insert is fast, so the 30 s ack deadline is not a concern.
- **Sender loop.** Polls every 1 s. Each pass claims one due row with `FOR UPDATE SKIP LOCKED`, renders, sends with the key, updates the row (setting `accepted_at` on success) and commits. If it found a row it loops again at once. The consumer insert does not trigger it. One row per transaction means a crash affects only that row. On a crash mid-send the lock is released and the row is retried with the same key, which MailRelay drops if the first send was accepted. A failed attempt 1 to 4 sets `next_attempt_at` to now plus 1, 2, 4 or 8 minutes; attempt 5 sets `failed`. A render exception counts as a failed attempt under the same policy (today it would roll back the whole batch and loop forever).
- **Result publisher.** Publishes the `sent` or `failed` result after the terminal state commits, then sets `result_published`. A loop republishes any terminal row with `result_published` false, so a restart or broker outage never loses a result.
- **Pager.** A separate loop pages on-call for `failed` rows with `paged_at IS NULL`, then sets `paged_at`. Paging is outside the send transaction, so an alerting outage cannot cause a sixth MailRelay attempt, and a failure is never left unpaged. A duplicate page after a crash is acceptable.

### Monolith parts

- **Old worker change:** it adds `AND type NOT IN (service-routed types)`, reading the flags at the start of each batch.
- **Forwarder** (polls every 1 s): selects `pending` rows of service-routed types `FOR UPDATE SKIP LOCKED`, regardless of `next_attempt_at` (the service honours the retry wait carried in the message). It re-checks the flag after taking the lock, publishes to `notifications.requested`, waits for the broker confirmation, sets `status='forwarded'` and commits. It does no rendering and no MailRelay call.
- **Result consumer:** `UPDATE ... SET status=outcome, attempts=attempts WHERE id=? AND status='forwarded'`. If the row is already terminal, ack as a no-op. If it is still `pending`, do not ack; redelivery 30 s later retries. That covers a result arriving before the forwarder commits.
- **Reconciler:** every 10 minutes it finds `forwarded` rows older than 1 hour with no result, republishes them and raises an alert. This is safe because the service dedupes by id: for a terminal id it republishes its stored result; for an id still in progress nothing changes. If the service is down, the alert is how a human learns of it, and the reconciler repeats every 10 minutes.

### What happens when things fail

| Failure | Result |
|---|---|
| Monolith crash after broker confirm, before the `forwarded` commit | Row stays `pending`, is republished; service dedupes |
| Lost broker confirmation | Same as above: treated as unpublished and republished (see residual risks) |
| Broker down, monolith side | Publishing fails, rows stay `pending`, forwarder retries each poll. Alert when the oldest forwardable row is older than 2 minutes. Nothing lost |
| Broker down, service side | Consumer receives nothing. Sender keeps working on stored rows. Results wait with `result_published` false and publish when the broker returns |
| Redelivered request | Conflict, no-op, ack |
| Service crash mid-send | Lock released; retry with the same key; MailRelay drops it if already accepted |
| MailRelay down | Rows retry on the policy, then fail and page |
| Result arrives before forwarder commit | Not acked; redelivered 30 s later |
| Service down long term | Reconciler alert; rows finish when the service returns |

## Rollout steps

### 1. Pass the idempotency key from the old worker

- **Starts:** a normal monolith deploy. First change shipped; no type has moved.
- **Change:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`. No data moves and no state changes.
- **Failures:** a crash after MailRelay accepts but before the batch commit leaves rows `pending`; the resend carries the same key and is dropped, which fixes the roughly 30 weekly duplicates. A timeout where MailRelay did accept also collapses to one email. The longest retry window is 15 minutes, inside the 24 h key life. During the rolling deploy, instances without the key behave as today.
- **Exit check:** a week of support duplicate reports drops to about zero. Confirm with MailRelay that the key behaves as documented.

### 2. Build the service, unused by production traffic

- **Starts:** a deploy of the new service. The monolith is unchanged.
- **Data:** none in production. Templates are copied into the service. Freeze template edits, or apply them to both copies, until decommission.
- **State:** the new service database described above, with the consumer, sender, result publisher and pager.
- **Exit check,** in staging against a MailRelay sandbox or a stub that honours `idempotency_key`:
  - Fault injection: kill the consumer after insert and before ack; kill the sender after the stub accepts and before commit; take the stub down for more than 15 minutes; take the broker down.
  - Render parity: for every stored payload of the three types, service output matches the monolith's `templates.render` byte for byte.
  - Each notification id produces exactly one accepted send.

### 3. Add the monolith side, dark

- **Starts:** a monolith deploy. All three flags are `monolith`, so behaviour does not change.
- **Changes:** add the `forwarded` status (no schema change is strictly needed, since the old worker selects only `pending`), the old worker filter, the forwarder, the result consumer and the reconciler.
- **Gate:** every monolith instance must run this version before any flag changes, or a stale old worker could ignore the filter. Check build versions on all instances.

### 4. Move `shipping_update`

- **Why first:** the brief fixes the order. It has no latency requirement and the highest volume, so it exercises the path hardest at the lowest risk. (This reasoning is mine; the brief gives only the order.)
- **Starts:** flip `notif.route.shipping_update=service`. It reaches all instances within 10 s.
- **Data:** new webhook notifications are inserted as today. The forwarder publishes each `pending` row, including rows with existing retry state, which keep their remaining attempts. The service sends and returns results.
- **State:** `pending` in the monolith until the broker confirms; then the service DB owns it; the terminal status is mirrored back.
- **Failures:** a row the old worker has locked at the flip stays with it until the batch commits; if it is scheduled for retry it is `pending` again and the forwarder takes it next poll. A stale instance within the 10 s window cannot double-send because of the row lock and status. Other failures as in the table above.
- **Soak:** at least 3 days, with these checks: rows forwarded equals rows inserted in the service equals results received; `forwarded` rows older than 1 hour is 0; duplicate-email reports are 0; failed rows are all paged; monolith CPU and DB connection use have dropped.
- **Rollback drill on day 1:** flip to `monolith`; confirm new rows are sent by the old worker; confirm rows already forwarded are still completed by the service; confirm no row is sent twice; flip back to `service`. The 3-day clock starts after the last flip back.
- **Rollback in general:** flip the flag. It takes effect within 10 s, inside the one-minute limit. Forwarded rows stay with the service and the old worker never picks them up. Unforwarded rows go to the old worker. In-flight rows are neither lost nor re-sent.

### 5. Move `order_confirmed`

- **Starts:** flip `notif.route.order_confirmed=service`, only after `shipping_update` has run on the service 3 or more days with clean checks.
- **Data, state, failures, rollback:** as step 4. Volume is 12,000 a day (about 0.14 a second), so capacity is no concern.
- **Added measurement:** p99 enqueue-to-MailRelay latency, from the row's `created_at` to `accepted_at`. The service holds both, computes the difference itself and emits it as a metric, so nothing extra goes to the monolith. Break it down by stage: forwarder wait, broker, service queue, send. A first-attempt MailRelay failure adds at least 1 minute, so the 60 s requirement holds only if first-attempt failures are well under 1%. Track that rate separately from service-caused latency.
- **Soak:** at least 3 days.

### 6. Move `password_reset`

- **Starts:** flip `notif.route.password_reset=service`, only when `order_confirmed` has run on the service 3 or more days and its measured p99 enqueue-to-MailRelay latency over that time is under 60 s. That is the proof the service path can meet `password_reset`'s own 60 s requirement.
- **Data, state, failures, rollback:** as step 5.
- **Extra safeguards:** alert when `password_reset` p99 exceeds 45 s over 15 minutes; alert when the oldest `pending` or `forwarded` `password_reset` row is older than 30 s; if p99 breaches 60 s and the cause is the service path, flip back at once.
- **Soak:** keep the old worker deployed and the flags in place for 7 days.

### 7. Decommission the old worker

- **Starts:** 7 days after step 6, with no rollback in that time and the step 5 and 6 checks clean.
- **Pre-checks:** zero `pending` rows owned by the monolith; zero `forwarded` rows older than 1 hour; the reconciler is quiet.
- **Changes, in order:** (1) remove `run_worker`, `_deliver` and any monolith template and MailRelay code nothing else uses; (2) make the forwarder forward every type unconditionally; (3) remove the three routing flags.
- **Kept:** `enqueue_notification`, the forwarder, the result consumer and the reconciler.
- **Failure behaviour:** afterwards, rollback to monolith sending is a code revert, not a flag flip. That is expected. During the rolling deploy, instances still running the old worker also honour the flags, which all say `service`, so none sends mail itself.

## Residual risks to review

- **24 h key window.** If a send is accepted and the service then stays down more than 24 h before retrying the row, the key has expired and the retry could duplicate. This is limited to the one row each instance has in progress. Alert when the service backlog ages past 1 hour.
- **Ambiguous broker confirm plus rollback.** The forwarder publishes, the confirmation is lost, the row stays `pending`, and the flag is then flipped to `monolith`. Both the old worker and the service can then send. Only the idempotency key prevents a duplicate, so this is safe only within 24 h. Runbook rule: if a broker outage has lasted more than 12 h, involve a human before flipping any flag back.
- **Staging fidelity.** Step 2 assumes a MailRelay sandbox or a stub that mimics the key behaviour. Confirm which exists before starting.

## Open questions

- The brief fixes the migration order but does not state why. The reasoning in step 4 is the author's inference.
