# Plan: Extract notifications into a Notification Service

## Starting point

- The monolith is our main application. Today it sends notifications from a background worker in the same process. That work competes with checkout for CPU and database connections.
- Three notification types exist. All are sent as email through MailRelay, our email-sending API:
  - `shipping_update`: about 40,000 a day.
  - `order_confirmed`: about 12,000 a day.
  - `password_reset`: about 1,500 a day. Users are waiting for these, so 99% of them (p99) must be sent within 60 seconds of being enqueued.
- MailRelay can drop a repeat send. If a send carries an `idempotency_key` (a unique ID for that send), and MailRelay already accepted a send with the same key in the last 24 hours, it drops the new one and reports success. We pass no key today.
- The worker commits once per batch of 50. If it crashes after MailRelay accepts some of the batch but before the commit, those rows are sent again. Support sees about 30 duplicate emails a week.
- The message broker is a queue shared with billing and search. It is at-least-once: a message not acknowledged within 30 seconds is redelivered, possibly to a different consumer. A publisher gets a confirmation once the broker has stored the message.
- Runtime flags are named settings that code reads while it runs. A change reaches every monolith instance within 10 seconds.

## Terms

- **Enqueue:** record a notification to be sent later. Business code does this inside its own database transaction, so the notification exists only if that transaction commits.
- **Monolith:** the main application, including its database and its `notifications` table.
- **Notification Service:** the new, separately deployed service that sends notifications. It has its own database.
- **Ack (acknowledge):** the consumer tells the broker it is done with a message, so the broker stops redelivering it.
- **Ledger:** the service's own table of every notification it has received, keyed by notification ID.
- **Lease:** a time-limited claim on a row. If the worker holding it dies, the lease expires and another worker can take the row.
- **`FOR UPDATE SKIP LOCKED`:** a database clause that lets several workers each take different rows at the same time, without waiting on each other.
- **Outbox:** a table where events are written in the same transaction as the change they describe. A relay later publishes them to the broker.
- **Handoff relay:** a process in the monolith that publishes committed notifications to the broker.
- **Terminal status:** `accepted` or `failed`. A row with a terminal status is finished.
- **Backoff:** the wait between retries: 1, 2, 4, then 8 minutes.
- **Page on-call:** send an alert to the engineer on call.
- **Stuck threshold:** an age limit after which a row counts as stuck. Its value is not set yet (see decision 12).
- **Fake MailRelay:** a test stand-in for MailRelay that copies its key-dedupe behavior.

## Invariants every step relies on

1. **One owner per row.** Each row in the monolith `notifications` table gets a new `owner` value:
   - `monolith`: the old worker may send it.
   - `handoff`: committed in the monolith but not yet confirmed on the broker. Only the handoff relay touches it. Nobody sends it.
   - `service`: confirmed on the broker. Only the Notification Service sends it. The monolith never sends it.

   The only allowed change to `owner` is `handoff` to `service`, made in one database transaction. The old worker selects only rows where `owner = 'monolith'`.

2. **Routing is decided per row, at enqueue.** `enqueue_notification` reads the flag `notifications.route.<type>`. If it says `service`, the row is inserted as `handoff`; otherwise it is inserted as `monolith`. If the flag read fails, the row is `monolith`. Because each row has exactly one owner, a wrong routing decision can delay a notification but can never duplicate it.

3. **Publish after commit, flip after confirmation.** The handoff relay reads only committed rows. It publishes each one, waits for the broker's confirmation, and then sets `owner = 'service'`. If it crashes between publishing and flipping, the row stays `handoff` and is published again. The service ignores the duplicate (invariant 4).

4. **The service ledger is keyed by notification ID.** The service inserts each received message with `ON CONFLICT (id) DO NOTHING` (a duplicate ID is silently skipped), commits, and then acks. The ack always comes after the commit and before any send. A redelivered message hits the conflict and does nothing. Sends are driven by ledger rows, not by messages, so duplicate messages cannot cause extra sends.

5. **Idempotency key on every send.** The old worker and the service both pass `idempotency_key = notification ID`. MailRelay's 24-hour dedupe is a second guard behind the ledger.

6. **Same retry policy on both sides.** A notification gets at most 5 attempts. The waits before attempts 2, 3, 4, and 5 are 1, 2, 4, and 8 minutes. If attempt 5 fails, the row is marked `failed` and on-call is paged. On the service, the attempt count is committed when an attempt starts, before the send. The old worker keeps its per-batch commit until its types move; step 1's idempotency key makes its resends safe.

7. **Rollback changes routing only for new rows.** Rows already owned by the service finish on the service. Rows owned by the monolith finish on the monolith. The handoff relay keeps draining `handoff` rows whatever the flag says. Every row has exactly one sender at any time.

## Steps

### Step 1. Pass the notification ID as `idempotency_key` on the old worker

- **Starts:** a one-line change in `_deliver`: `mailrelay.send(..., idempotency_key=str(row.id))`. No type has moved.
- **Data moves:** none. Each send now carries its row ID.
- **State lives:** MailRelay's 24-hour dedupe store. The monolith `notifications` table is unchanged.
- **On failure:**
  - Crash mid-batch: the resend carries the same key, so MailRelay drops it if the first send was accepted within the last 24 hours.
  - MailRelay down: the existing error path and backoff apply, unchanged.
  - MailRelay rejects the parameter: roll back the deploy. Do not start step 2.
- **Gate to step 2:** in staging, sending the same key twice yields one delivery. In production, confirm MailRelay accepts the key. Track the weekly duplicate count (baseline about 30) as evidence that it works.

### Step 2. Monolith: owner column, routing flags, handoff relay, status consumer, alerts

This step only prepares the monolith. Nothing is sent to the service yet.

- **Starts:** deploy an online, non-blocking migration (one that does not lock the table for long). It:
  - Adds `owner`, with default `'monolith'`, so existing rows stay monolith-owned.
  - Adds an index on `(owner, status, next_attempt_at)`.
  - Sets up the flags `notifications.route.<type>` for all three types, each set to `monolith`.
- **Also in this step:** ship the old worker change so its select adds `owner = 'monolith'`. Without this, the old worker could send `handoff` and `service` rows.
- **Data moves:** none, because no type is routed to the service.
- **Enqueue:** the signature is unchanged, so business code does not change. Inside the caller's transaction, insert with `owner = 'handoff'` when the route flag is `service`, otherwise `'monolith'`. If the flag read fails, use `'monolith'`.
- **Handoff relay** (runs on every instance; `SKIP LOCKED` lets instances split the work):
  - Selects committed rows with `owner = 'handoff'`, in batches.
  - Publishes `{schema_version, id, type, user_id, email, payload, created_at}` to the broker.
  - After broker confirmation, runs `UPDATE ... SET owner = 'service' WHERE id = ? AND owner = 'handoff'`.
  - Keeps running whatever the flag says.
  - Backstop (a safety net for lost messages): republishes rows that are `owner = 'service'` but have no terminal status after the stuck threshold. This is safe because the service ignores IDs it already has, as long as ledger retention (step 3) is longer than the threshold.
- **Status consumer:** reads `accepted` and `failed` events from the service and copies them into `status`, but only for rows where `owner = 'service'`. This is for support visibility only. Dispatch (the sending logic) never reads `status`.
- **State lives:** the monolith database only.
- **On failure:**
  - Crash after publish, before the flip: the row stays `handoff`, is published again, and the service ignores it.
  - Broker down: rows stay `handoff`, and the relay retries with backoff. Alert when the oldest `handoff` row is older than 2 minutes.
  - MailRelay: not involved in this step.
  - Redelivered status event: the conditional update changes nothing the second time.
- **Alerts:** the oldest `handoff` row is too old, or a `service` row has no terminal status after the stuck threshold.

### Step 3. Build the Notification Service

- **Starts:** a new service with its own database. The monolith never connects to that database, and the service never connects to the monolith's database. The broker is the only link between them. Deploy with the consumer on a test topic only.
- **Components:**
  - **Consumer:** reads messages from the broker.
  - **Ledger table `notifications`:** columns `id` (primary key), `type`, `user_id`, `email`, `payload`, `schema_version`, `status` (`received` | `sending` | `retry_wait` | `accepted` | `failed`), `attempts`, `lease_until`, `next_attempt_at`, `last_attempt_at`, `accepted_at`, `last_error`, and `received_at`.
  - **Renderer:** builds the email subject and body from the template and payload. The three templates are copied in. The monolith's copies stay until decommission.
  - **Sender:** calls MailRelay with `idempotency_key = id`.
  - **Worker:** claims rows, renders them, sends them, and records the outcome.
  - **Status publisher:** an outbox table `status_events`, relayed to the broker.
- **Receive:** `INSERT ... ON CONFLICT (id) DO NOTHING`, then commit, then ack.
- **Worker claim:** a row is claimable if any of these is true:
  - Its status is `received`.
  - Its status is `retry_wait` and `next_attempt_at <= now()`.
  - Its status is `sending` and its `lease_until` has passed. The worker that held it died.

  In one transaction, select claimable rows using `FOR UPDATE SKIP LOCKED`. Set `status = 'sending'`, `attempts = attempts + 1`, `last_attempt_at = now()`, and `lease_until = now() + LEASE`. Then commit. `LEASE` must be longer than the MailRelay timeout, so a send still in progress never looks abandoned.
- **Ambiguity rule:** a claimed row is not sent, because an earlier send may already have reached MailRelay and its result is unknown. This applies if either of these is true:
  - The row's attempt count was already 5 before this claim. Attempt 5 started, but no outcome was recorded.
  - The row's last attempt started more than 20 hours ago. The 20-hour margin keeps every resend inside MailRelay's 24-hour dedupe window.

  Such a row is marked `failed`, and on-call is paged with the reason "outcome unknown". It is not sent.
- **Send:** render the notification, then call MailRelay. The send happens outside any database transaction; the claim has already been committed.
  - Success: in one transaction, set `accepted` and `accepted_at`, and write a `status_events` row.
  - Any error while rendering or sending, with `attempts < 5`: set `retry_wait` and `next_attempt_at = now() + BACKOFF[attempts - 1]`.
  - Any error while rendering or sending, with `attempts = 5`: set `failed`, write a `status_events` row, and page on-call.
- **Deliberate differences from today:**
  - Attempts are counted at claim time, so a crash uses up an attempt. This limits crash loops (a process that keeps crashing on the same row).
  - A render error counts as an attempt. After 5 tries the row goes to `failed` and pages on-call. Today a render error retries silently forever.
- **Ledger retention:** at least 30 days. It must be longer than the broker's retention window and the stuck threshold, so a redelivered message is always caught by the ledger.
- **On failure:**
  - Crash mid-send: the lease expires, another worker reclaims the row with the same key, and MailRelay drops the send if the earlier one was accepted within 24 hours. If more than 20 hours have passed, the ambiguity rule applies instead.
  - Broker down: the consumer stops, messages wait on the broker, and rows already received keep being sent.
  - MailRelay down: the row goes to `retry_wait` and follows the 1, 2, 4, 8 minute schedule.
  - Redelivery: the insert conflicts, the message is acked, and nothing is sent again.

### Step 4. Prove the service in staging before any production routing

- **Starts:** the service in staging, with a fake MailRelay that enforces the 24-hour key dedupe.
- **Data moves:** recorded production payloads, with email addresses masked. Each payload is rendered by both the monolith and the service, and the outputs are compared byte for byte.
- **Required tests:**
  - One message delivered three times produces one send.
  - Worker killed after MailRelay accepts but before the commit: exactly one `accepted`.
  - Relay crashed after publish but before the flip: exactly one send.
  - Broker down for 10 minutes, then up: no loss and no duplicate.
  - MailRelay returns 5xx on every attempt: exactly one `failed` and one page, with the 1, 2, 4, 8 minute schedule between attempts.
  - Render exception: `failed` and a page after 5 claims.
  - Flip one type to `service` and back mid-stream, with rows in both states: each ID is sent exactly once.
- **Gate:** all tests pass, and the fake's key behavior matches the step 1 result.

### Step 5. Cut over `shipping_update`

- **Starts:** set `notifications.route.shipping_update = service` in production. The flag reaches every instance within 10 seconds.
- **Data moves:** new `shipping_update` rows go from monolith enqueue, to the `handoff` relay, to the broker, to the service ledger. Rows already `pending` in the monolith finish there, so nothing moves mid-flight.
- **State lives:** the monolith row's `owner` and `status` (the status is a copy written back from the service), and the service ledger.
- **Gate to step 6:** at least 3 days on the service, and all of the following:
  - No ID has more than one `accepted`.
  - No ID is both sent by the monolith and accepted by the service.
  - No row is past the stuck threshold in `handoff`, or in `service` without a terminal status.
  - The `failed` count is within the normal range.
- **Rollback rehearsal:** within the 3-day window, flip the route back to `monolith` for a few minutes. Confirm new rows land on the monolith, then flip forward again. Confirm no ID is sent twice.
- **Rollback procedure (applies to steps 5 to 7):** set the flag to `monolith`. New rows become `monolith`-owned within about a minute. `handoff` rows keep publishing. Service-owned rows keep sending on the service. The service stays up until its non-terminal rows are drained.
- **On failure:**
  - Service down: rows wait on the broker. Confirm the broker's retention covers the outage. Rollback stops new handoffs but does not stop the service.
  - Broker down: `handoff` rows wait in the monolith. No second path is needed.

### Step 6. Cut over `order_confirmed`

- **Starts:** the step 5 gate is met. Set `notifications.route.order_confirmed = service`.
- **Data moves:** the same path as step 5, for about 12,000 rows a day.
- **Latency measurement:** `accepted_at` (service) minus `created_at` (monolith commit time), tracked as p99 over rolling daily windows and over the full window.
  - Keep the relay poll interval at 1 second or less.
  - The service acks before it sends, so the broker's 30-second redelivery timeout does not fire during a normal send.
  - Check clock skew between the monolith database and the service before trusting the number. The two timestamps come from different clocks.
- **Gate to step 7:** at least 3 days on the service, and p99 enqueue-to-accepted under 60 seconds over the whole window and in every daily window. If the gate fails, `password_reset` stays on the monolith.
- **On failure:** as in step 5.

### Step 7. Cut over `password_reset`

- **Starts:** the step 6 latency gate is met. Run the rollback rehearsal from step 5 first. Then set `notifications.route.password_reset = service`.
- **Data moves:** about 1,500 rows a day, which users are actively waiting for. Watch the p99 and the stuck-row alerts closely.
- **State lives:** the same as step 5.
- **On failure:** the rollback procedure applies. Flipping back is safe at any time, because each row has exactly one sender.

### Step 8. Decommission the old worker

- **Starts:** 7 days after the `password_reset` flip, with no rollback in that window, and all of the following true:
  - No `monolith`-owned rows are still non-terminal (`pending`). Older rows that were already sent or failed do not block this.
  - No rows are `handoff`.
  - No non-terminal service rows are past the threshold.
  - Status feedback is fully consumed.
- **Action:**
  - Remove `run_worker`, `_deliver`, the moved template code, the handoff relay, and the status consumer.
  - Drop the `owner` column in a later migration, in a separate deploy.
- **Why the wait:** the old worker stays in the build for those 7 days, so a rollback in that window is still just a flag flip.
- **On failure:** if any gate is not met, remove nothing. Investigate first.

## Decisions to confirm and open risks

1. **Crash counts as an attempt.** Today's worker counts only MailRelay errors. The plan counts every claim, including claims that end in a crash. This is stricter. Confirm.
2. **Render errors page after 5 tries.** Today they retry silently forever. Confirm.
3. **Email addresses on the broker.** The service cannot read the monolith database, so each message must carry the email address. The broker is shared with billing and search, so access control or encryption may be required.
4. **MailRelay timeout.** `LEASE` depends on it, and the 20-hour ambiguity margin depends on MailRelay's 24-hour window. The brief does not give the timeout.
5. **Retention.** Broker retention must exceed the longest acceptable service outage. Ledger retention must exceed the stuck threshold.
6. **Ordering.** Messages are not ordered across rows. Two `shipping_update` emails for the same shipment could arrive out of order. Confirm whether that matters.
7. **Template ownership.** Once a type moves, template changes for it ship with the service, not the monolith.
8. **Flag store unavailable.** The design assumes `flags.get` can fail, and it falls back to `monolith`.
9. **Status mirror.** Dispatch does not depend on it; it exists for support visibility. Confirm it is wanted.
10. **Clock skew** affects the p99 gate in step 6.
11. **Source limits.** This plan uses only the brief and the two files it names. It does not cover the broker's actual retention, MailRelay's real timeout, or the flag client's caching. Check these before step 3.
12. **Stuck threshold.** The brief does not set this value. It is used by the step 2 backstop and the step 5 gate. It must be longer than normal send time and shorter than ledger retention (30 days). Set it before step 2.