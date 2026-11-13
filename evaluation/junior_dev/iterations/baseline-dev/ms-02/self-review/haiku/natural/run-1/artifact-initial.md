# Plan: Extract notifications into a Notification Service

## Starting point

- Three email-only types go through MailRelay: `shipping_update` (40,000/day), `order_confirmed` (12,000/day), `password_reset` (1,500/day, p99 under 60 s required).
- MailRelay dedupes on `idempotency_key` for 24 hours. We pass no key today.
- The monolith worker commits once per batch, so a crash after MailRelay accepts some rows causes resends (about 30 duplicates a week).
- The broker is at-least-once. Unacknowledged messages are redelivered after 30 s. Publishers get confirmation once a message is stored.
- Flags reach every monolith instance within 10 s.

## Invariants every step relies on

1. **One owner per row.** Each `notifications` row is owned by exactly one party at a time, recorded in a new `owner` column:
   - `monolith`: the old worker may send it.
   - `handoff`: committed in the monolith, not yet confirmed on the broker. Only the handoff relay touches it. Nobody sends it.
   - `service`: confirmed on the broker. Only the Notification Service sends it. The monolith never sends it.
   Transitions only move forward, each in a single DB transaction. The old worker selects only `owner = 'monolith'`.
2. **Routing is decided at enqueue, per row.** `enqueue_notification` reads `notifications.route.<type>`. If the flag is `service`, the row is inserted as `handoff`. Otherwise it is `monolith`. If the flag read fails, the row is `monolith`. Because ownership is per row and single-owner, routing mistakes can cause delay but never duplicates.
3. **Publish after commit, flip after confirmation.** The relay reads only committed rows. It publishes, waits for broker confirmation, then sets `owner = 'service'`. A crash between publish and flip leaves the row `handoff`, so it is republished. The service dedupes.
4. **Service ledger keyed by notification id.** The service inserts each received message with `ON CONFLICT (id) DO NOTHING`, commits, then acks. Acks come after the commit, never after the send. Redelivery is a no-op. Sends are driven by ledger rows, not by messages, so duplicate messages cannot cause extra sends.
5. **Idempotency key on every send.** Both sides pass `idempotency_key = notification id`. MailRelay's 24-hour window is a second guard. The ledger is the primary guard.
6. **Same retry policy on both sides.** Attempts are persisted before each send. Backoff is 1, 2, 4, 8 minutes. A failure on attempt 5 marks the row `failed` and pages on-call.
7. **Rollback only changes routing for new rows.** Rows already owned by the service finish on the service. Rows owned by the monolith finish on the monolith. The handoff relay keeps draining `handoff` rows whatever the flag says. A row never gets a second sender.

## Steps

### Step 1. Pass the notification id as `idempotency_key` on the old worker

- **Starts:** a one-line deploy in `_deliver`: `mailrelay.send(..., idempotency_key=str(row.id))`. No type has moved.
- **Data moves:** none. Each send now carries its row id.
- **State lives:** MailRelay's 24-hour dedupe store. The monolith `notifications` table is unchanged.
- **On failure:**
  - Crash mid-batch: the resend carries the same key, so MailRelay drops it if the first send was accepted within 24 hours.
  - MailRelay down: the existing error path and backoff apply, unchanged.
  - MailRelay rejects the parameter: roll back the deploy. Do not start step 2.
- **Gate to step 2:** in a staging test, sending the same key twice yields one delivery. In production, confirm the key is accepted. Track the weekly duplicate count (baseline about 30) as evidence.

### Step 2. Monolith: ownership column, routing flag, handoff relay, status consumer, invariant alerts

- **Starts:** deploy with an online, non-blocking migration:
  - Add `owner` with default `'monolith'`. Existing rows stay monolith-owned.
  - Add an index on `(owner, status, next_attempt_at)`.
  - Create flags `notifications.route.<type>` for all three types, all set to `monolith`.
- **Data moves:** none yet, because no type is routed to the service.
- **Enqueue:** signature unchanged. Inside the caller's transaction, insert with `owner = 'handoff'` when the route is `service`, otherwise `'monolith'`.
- **Handoff relay (every instance, `SKIP LOCKED`):**
  - Selects committed rows with `owner = 'handoff'` in batches.
  - Publishes `{schema_version, id, type, user_id, email, payload, created_at}`.
  - After broker confirmation, runs `UPDATE ... SET owner = 'service' WHERE id = ? AND owner = 'handoff'`.
  - Runs whatever the flag says.
  - Backstop: republishes `owner = 'service'` rows that have no terminal status after a threshold. This is safe because the service ledger dedupes by id, provided ledger retention exceeds the threshold (see step 3).
- **Status consumer:** reads `accepted` and `failed` events from the service and mirrors them into `status`, guarded by `WHERE owner = 'service'`. It is for support visibility only and never affects dispatch.
- **State lives:** the monolith DB only.
- **On failure:**
  - Crash after publish, before the flip: the row stays `handoff`, is republished, and the service dedupes.
  - Broker down: rows stay `handoff`. The relay retries with backoff. Alert when the oldest `handoff` row is older than 2 minutes.
  - MailRelay: not involved in this step.
  - Redelivered status event: the conditional update is idempotent.
  - Alerts: fire on the oldest `handoff` row, and on `service` rows without a terminal status after a threshold.

### Step 3. Build the Notification Service

- **Starts:** a new service and its own database, which the monolith never connects to. Deploy it with the consumer on a test topic only.
- **Components:**
  - Consumer.
  - Ledger table `notifications`: `id` (PK), `type`, `user_id`, `email`, `payload`, `schema_version`, `status` (`received` | `sending` | `retry_wait` | `accepted` | `failed`), `attempts`, `lease_until`, `next_attempt_at`, `last_attempt_at`, `accepted_at`, `last_error`, `received_at`.
  - Renderer, with the three templates moved in. The monolith copies stay until decommission.
  - Sender, which calls MailRelay with `idempotency_key = id`.
  - Worker.
  - Status publisher: an outbox table `status_events` relayed to the broker.
- **Receive:** `INSERT ... ON CONFLICT (id) DO NOTHING`, commit, then ack.
- **Worker claim:** one transaction selects `received` or `retry_wait` rows with `next_attempt_at <= now()` and no live lease, using `FOR UPDATE SKIP LOCKED`. It sets `status = 'sending'`, `attempts = attempts + 1`, `last_attempt_at = now()`, and `lease_until = now() + LEASE`, then commits. `LEASE` must exceed the MailRelay timeout.
- **Ambiguity rule:** a claimed row with `attempts` already at 5, or whose last attempt started more than 20 hours ago, is marked `failed` and paged as "outcome unknown". It is not resent.
- **Send:** render, then call MailRelay outside the transaction.
  - Success: set `accepted`, `accepted_at`, and write a `status_events` row in the same transaction.
  - Error with `attempts < 5`: set `retry_wait`, `next_attempt_at = now() + BACKOFF[attempts - 1]`.
  - Error with `attempts = 5`: set `failed`, write the event, and page on-call.
- **Deliberate differences from today:**
  - Attempts are counted at claim, so a crash consumes an attempt. This bounds crash loops.
  - A render error counts as an attempt and reaches `failed` plus a page after 5 tries. Today it retries silently forever.
- **Ledger retention:** at least 30 days, which must exceed the broker retention window and the reconciliation threshold.
- **On failure:**
  - Crash mid-send: the lease expires, the row is reclaimed with the same key, and MailRelay dedupes if the earlier send was accepted within 24 hours.
  - Broker down: the consumer stops, messages wait on the broker, and already-received rows keep draining.
  - MailRelay down: `retry_wait` with the 1/2/4/8 schedule.
  - Redelivery: the insert conflicts, the message is acked, and nothing is sent again.

### Step 4. Prove the service in staging before any production routing

- **Starts:** the service in staging, with a fake MailRelay that enforces the 24-hour key dedupe.
- **Data moves:** recorded production payloads, with emails masked. Each is rendered by both the monolith and the service, and the output is compared byte for byte.
- **Required tests:**
  - Triple redelivery of one message produces one send.
  - Kill the worker after MailRelay accepts but before commit: exactly one accepted.
  - Crash the relay after publish but before the flip: exactly one send.
  - Broker down for 10 minutes, then up: no loss, no duplicate.
  - MailRelay 5xx on every attempt: exactly one `failed` and one page, with the 1/2/4/8 schedule.
  - Render exception: `failed` and a page after 5 claims.
  - Flip one type to `service` and back mid-stream with rows in both states: each id is sent exactly once.
- **Gate:** all tests pass, and the fake's key behaviour matches the step 1 result.

### Step 5. Cut over `shipping_update`

- **Starts:** set `notifications.route.shipping_update = service` in production. The flag reaches every instance within 10 s.
- **Data moves:** new `shipping_update` rows go monolith enqueue, then `handoff` relay, then broker, then service ledger. Rows that are already `pending` in the monolith finish there, so nothing moves mid-flight.
- **State lives:** the monolith row `owner` and `status` mirror, and the service ledger.
- **Gate to step 6:** at least 3 days on the service, plus:
  - No id has more than one `accepted`.
  - No id is both monolith-sent and service-accepted.
  - No row is past the stuck threshold in `handoff`, or in `service` without a terminal status.
  - `failed` count is within the normal range.
- **Rollback rehearsal:** within the 3-day window, flip the route back to `monolith` for a few minutes, confirm new rows land on the monolith, then flip forward. Confirm no id is sent twice.
- **Rollback procedure (applies to steps 5 to 7):** flip the flag to `monolith`. New rows become `monolith`-owned within about a minute. `handoff` rows keep publishing. Service-owned rows keep sending on the service. The service stays up until its non-terminal rows are drained.
- **On failure:**
  - Service down: rows wait on the broker. Confirm broker retention covers the outage. Rollback stops new handoffs but does not stop the service.
  - Broker down: `handoff` rows wait in the monolith. There is no second path, and none is needed.

### Step 6. Cut over `order_confirmed`

- **Starts:** the step 5 gate is met. Set `route.order_confirmed = service`.
- **Data moves:** the same path as step 5 for 12,000 rows a day.
- **Latency measurement:** `accepted_at` (service) minus `created_at` (monolith commit time), tracked as p99 in rolling daily windows and over the full window.
  - Keep the relay poll interval at 1 s or less.
  - Ack-before-send means the 30 s redelivery timeout never fires during a normal send.
  - Check clock skew between the monolith DB and the service before trusting the number.
- **Gate to step 7:** at least 3 days on the service, and p99 enqueue-to-accepted under 60 s over the whole window and every daily window. If the gate fails, `password_reset` stays on the monolith.
- **On failure:** as in step 5.

### Step 7. Cut over `password_reset`

- **Starts:** the step 6 latency gate is met. Set `route.password_reset = service`. Run the rollback rehearsal from step 5 first.
- **Data moves:** about 1,500 rows a day, which users are actively waiting for. Watch the p99 and the stuck-row alerts closely.
- **State lives:** same as step 5.
- **On failure:** the rollback procedure applies. Flipping back is safe at any time, because each row has one sender.

### Step 8. Decommission the old worker

- **Starts:** 7 days after the `password_reset` flip, with no rollback in that window, and all of the following true:
  - No `monolith`-owned rows.
  - No `handoff` rows.
  - No non-terminal service rows past the threshold.
  - Status feedback fully consumed.
- **Action:**
  - Remove `run_worker`, `_deliver`, the moved template code, the handoff relay, and the status consumer.
  - Drop the `owner` column in a later migration, in a separate deploy.
- **Why the wait:** the old worker stays in the build until the 7 days pass, so a rollback during that window is still a flag flip.
- **On failure:** if any gate is not met, do not remove anything. Investigate first.

## Decisions to confirm and open risks

1. **Crash counts as an attempt.** Today's worker counts only MailRelay errors. The plan counts claims. This is stricter. Confirm.
2. **Render errors page after 5 tries.** Today they retry silently forever. Confirm.
3. **Email addresses on the broker.** The service cannot read the monolith DB, so the message must carry the email. The broker is shared with billing and search. Access control or encryption may be required.
4. **MailRelay timeout.** `LEASE` depends on it. The brief does not give it.
5. **Broker retention** must exceed the longest acceptable service outage. Ledger retention must exceed the reconciliation window.
6. **Ordering.** Messages are not ordered across rows. Two `shipping_update` emails for the same shipment could arrive out of order. Confirm whether that matters.
7. **Template ownership.** Once a type moves, no template change for it is made in the monolith. Template changes ship with the service.
8. **Flag store unavailable.** The design assumes `flags.get` can fail, and falls back to `monolith`.
9. **Status mirror.** Dispatch does not depend on it. It is needed for support visibility. Confirm it is wanted.
10. **Clock skew** affects the p99 gate (step 6).
11. **Source limits.** This plan uses only the brief and the two files named in it. It does not cover the broker's actual retention, MailRelay's real timeout, or the flag client's caching. Those need checking before step 3.