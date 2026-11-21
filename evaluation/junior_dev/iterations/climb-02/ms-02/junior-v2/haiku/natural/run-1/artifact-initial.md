# Plan: Extract notifications into a Notification Service

## Starting point (from the existing files)

- Today `run_worker` polls `notifications` every 5 s, takes up to 50 `pending` rows with `FOR UPDATE SKIP LOCKED`, sends each one, and commits once per batch. A crash after MailRelay accepts a send but before the commit re-sends the row. That is the cause of the ~30 duplicates a week.
- MailRelay drops a send whose `idempotency_key` it accepted in the last **24 hours**. Our retry span is short: backoff 1+2+4+8 = 15 minutes, plus timeouts. So a key covers every retry in the policy. It does not cover a message that arrives more than a day after its first send.
- The broker is at-least-once. It redelivers a message that is not acked within 30 s, possibly to another consumer. Publishers get a confirm once a message is stored.
- Flags reach every monolith instance within 10 s. The old worker polls every 5 s, so a flag flip plus the poll is well inside one minute.
- Volume is about 40,000 `shipping_update`, 12,000 `order_confirmed` and 1,500 `password_reset` per day, all email through MailRelay.

## Invariants the plan keeps

- **I1. One owner per row.** Each `notifications` row is routed once, at enqueue time, to either `monolith` or `service`. Only the owner may send it. The old worker selects only `route = 'monolith' AND status = 'pending'`. Nothing else sends a `monolith` row.
- **I2. Every MailRelay send carries `idempotency_key` = the notification id.** The key is set when the row is created and is reused on every retry.
- **I3. Every consumer dedupes by notification id and acks only after its own commit.** Redelivery and republish are therefore harmless.
- **I4. No resend past the key window.** If an earlier send attempt for an id is in doubt (it was started, no outcome was recorded) and it started more than 20 hours ago, the id is not sent again. It is marked failed and on-call is paged. The 20-hour margin sits inside MailRelay's 24-hour window.
- **I5. Flags only affect new enqueues.** The publisher, the status path and the old worker's rows ignore flags. A rollback never moves rows that already exist.

## Schema changes

**Monolith `notifications` table** (all additions are nullable or defaulted, so they are metadata-only changes):
- `route` text, default `'monolith'`. Values: `monolith` or `service`.
- `status` gains a value, `handed_off`. Meaning: the service owns the row and the monolith is waiting for an outcome.
- `handed_off_at` timestamp.
- `shadow_published_at` timestamp. Used only by shadow publishing (step 5).

**Service database** (separate, owned only by the service):
- `inbox`: `id` (primary key, the notification id), `type`, `user_id`, `email`, `payload`, `created_at` (monolith clock), `state` (`queued`, `retry`, `sent`, `failed`), `attempts`, `next_attempt_at`, `claimed_until`, `send_started_at`, `accepted_at`, `last_error`, `received_at`.
- `outbox`: status events waiting to be published to the broker (`notification.status`).
- `shadow`: rendered output and timing for shadow copies, if shadow mode is used (step 4).

## Message contracts

- **`notification.requested`** (monolith to service), versioned with `v`. Fields: `id`, `type`, `user_id`, `email`, `payload`, `created_at`. The payload must be self-contained. Rendering may not read the monolith database (step 3 checks this).
- **`notification.status`** (service to monolith). Fields: `id`, `status` (`sent` or `failed`), `attempts`, `accepted_at` or `failed_at`, `last_error` (truncated). Terminal events only.
- **`notification.shadow`** (monolith to service, shadow topic only). Same fields as `notification.requested`. The service renders and records. It never calls MailRelay.

## Plan

### Step 1. Send with the notification id as `idempotency_key` in the old worker

- **Starts when:** the change is merged and deployed to the monolith. No flag, no schema change.
- **Data that moves:** nothing new. The key is `row.id`, passed to `mailrelay.send(...)` on every attempt, including retries.
- **State lives:** MailRelay's 24-hour key store, plus the existing `notifications` table.
- **If it fails:**
  - *Crash after MailRelay accepted, before commit:* the batch rolls back, the row is picked up again within 5 s, and MailRelay drops the repeat under the same key. Within the window this is no longer a duplicate.
  - *MailRelay down or timing out:* unchanged. Each timeout counts as a failed attempt. The next attempt reuses the key, so a send that was accepted despite a timeout is not doubled.
  - *Broker:* not involved.
  - *Redelivery:* not involved.
- **Verify and roll back:** duplicate-email support tickets should fall toward zero. Rollback is a plain code revert. No data changes.

### Step 2. Add routing and the `handed_off` state, with every flag defaulting to monolith

- **Starts when:** the migration runs, then the code deploys.
- **Data that moves:** none. Every existing row gets `route = 'monolith'`.
- **State lives:** monolith `notifications` (new `route` column, new status value, `handed_off_at`).
- **Changes:**
  - `enqueue_notification` keeps its signature and still inserts inside the caller's transaction. It sets `route = 'service'` only when `flags.get("notifications.route.<type>") == "service"`. Anything else, including a flag read error, gives `monolith`.
  - The old worker's select gains `AND route = 'monolith'`. This enforces I1 before any row can be routed to the service. Add a test where a `route = 'service'` pending row is never picked up by the old worker.
- **If it fails:**
  - *Flag store unavailable:* enqueue falls back to `monolith`. Checkout is never blocked.
  - *Crash:* the enqueuing transaction is all or nothing, as today.
  - *Broker and MailRelay:* not involved.
- **Roll back:** revert the code. The added column and status value are harmless if left in place.

### Step 3. Check and freeze the rendering contract

- **Starts when:** a developer audit, then a PR.
- **Data that moves:** none at runtime.
- **Work:**
  - Confirm that `templates.render` reads only its `(type, payload)` arguments. If any template reads the monolith database, add those fields to the payload at enqueue time. The payload then carries the data the service needs, so the service never reads the monolith database.
  - Copy the templates into a shared package that both sides can import. The service uses it, and the monolith keeps it only until step 11.
  - Add golden tests. For sample payloads of each type, the copied templates must produce byte-identical subject and body to the monolith's current output.
- **If it fails:** a template that reads the database blocks the cutover. Fix it here, before any service exists.

### Step 4. Build the Notification Service with its own database, receiving no traffic

- **Starts when:** the service is deployed. Nothing in the monolith points at it yet.
- **Data that moves:** none yet.
- **State lives:** the service database (`inbox`, `outbox`, and `shadow` if used). Its MailRelay credentials are separate from the monolith's.
- **Components:**
  - **Consumer.** For each `notification.requested` message: in one transaction, `INSERT ... ON CONFLICT (id) DO NOTHING` into `inbox` with `state = 'queued'`. Commit, then ack. Never ack before commit.
  - **Sender.** Claims due rows with `FOR UPDATE SKIP LOCKED`, sets `claimed_until` (lease longer than MailRelay's timeout plus a margin), and sets `send_started_at` on each claim. It commits the claim before calling MailRelay. Then it renders, sends with `idempotency_key = id`, and records the outcome.
  - **Retry policy.** Attempts increment only on a recorded failure. On the 5th failure it sets `failed`, writes a status event, and pages on-call. Waits are 1, 2, 4, 8 minutes. This matches today's policy.
  - **Status outbox.** Publishes terminal status events and marks each one published only after the broker confirms.
  - **Shadow consumer** (if used). Renders and records only. It refuses to call MailRelay. A startup check fails the process if shadow mode and a MailRelay client are both enabled.
- **If it fails:**
  - *Crash between MailRelay accepting and the outcome commit:* the lease expires, the row is reclaimed, and it is sent again with the same key. MailRelay drops it. The attempt count was not changed, so the crash does not consume an attempt. Today's crash behaviour is the same. Rule I4 applies if the lease expires after more than 20 hours.
  - *Broker down:* the consumer waits and reconnects. Nothing is acked, so nothing is lost.
  - *MailRelay down:* normal retries and failure, as above.
  - *Redelivery:* the insert conflicts, the duplicate is acked, and the existing row is not touched.

### Step 5. Monolith handoff: publisher, status consumer, sweep, and shadow publishing

- **Starts when:** the monolith deploys these background loops. Still no row is routed to the service.
- **Data that moves:**
  - **Publisher.** Each `route = 'service' AND status = 'pending'` row is published as `notification.requested`. The row is then set to `handed_off` and `handed_off_at` is recorded. Each row is handled in its own short transaction. The row lock is held across the broker confirm.
  - **Status consumer.** Applies `notification.status` with `UPDATE ... SET status, attempts WHERE id = ? AND status = 'handed_off'`. Acks after commit.
  - **Shadow publisher** (optional, recommended). Publishes `notification.shadow` for rows where `shadow_published_at IS NULL`, then stamps that column. Shadow copies never change the row's status.
- **State lives:** monolith `notifications` for the handoff state. The broker for the messages in flight.
- **Sweep and pages:** every minute, page on-call when:
  - a `route = 'service'` row is still `pending` after 5 minutes (publisher stalled), or
  - a row has been `handed_off` for more than 1 hour without a status event.
  - A sweep page never triggers a resend.
- **If it fails:**
  - *Publisher crashes after broker confirm, before marking:* the row stays `pending` and is published again. The service dedupes on id (I3). No duplicate send.
  - *Broker down:* no confirm, so the row stays `pending`. Enqueue still succeeds, because it writes only to the database. The sweep pages after 5 minutes.
  - *Status consumer redelivery:* the conditional update matches nothing. No-op.
  - *Service down:* messages wait in the broker. Rows stay `handed_off`. The sweep pages after 1 hour.

### Step 6. Shadow soak and parity check

- **Starts when:** step 5 has been live.
- **Data that moves:** shadow copies of all notifications, rendered by the service and compared with the monolith's rendering of the same payloads.
- **Gate to leave this step (recommended, not in the brief):** at least 3 days with zero render mismatches, and the service's shadow queue depth stays bounded at peak load.
- **If it fails:** a render mismatch blocks cutover. Fix the templates or the payload contract and go back to step 3. Shadow copies cannot send mail, so no user is affected.

### Step 7. Cut over `shipping_update` (flag flip to `service`)

- **Starts when:** steps 1 to 6 are complete and the sweep alerts are confirmed to fire in a test.
- **Data that moves:** new `shipping_update` enqueues get `route = 'service'`. They go publisher, then service, then status back to the monolith row.
- **State lives:** the monolith row (`pending`, then `handed_off`, then `sent` or `failed`). The service inbox for the send itself.
- **Dwell:** at least 3 days. Watch the sweep alerts, MailRelay duplicate-key drops, support duplicate tickets, and the retry and failure rates.
- **Rows already in flight:** rows routed to the monolith before the flip are sent by the old worker. Rows routed after the flip are sent by the service. The route is fixed per row (I1), so the two paths never overlap.
- **If it fails:** see step 10 for the rollback procedure. Rollback for this type is the same flag flip in reverse.

### Step 8. Cut over `order_confirmed`

- **Starts when:** step 7 has run for at least 3 days with no unresolved sweep pages or duplicate reports.
- **Data that moves:** the same as step 7, for `order_confirmed`. This is the type that matters most to checkout, but checkout's cost is unchanged. The enqueue path adds only a flag read and a column value. The publisher is asynchronous and runs off the checkout path.
- **Dwell:** at least 3 days. This dwell is also the measurement window for the latency gate in step 9.
- **If it fails:** same as step 7. Roll back this type only. `shipping_update` stays on the service.

### Step 9. Latency gate before `password_reset`

- **Starts when:** step 8's dwell is complete.
- **Measurement:** on the service, for accepted `order_confirmed` sends, `latency = accepted_at − created_at`. `created_at` comes from the monolith's database clock, so check clock skew between the two hosts. p99 must be under 60 seconds.
- **Decision required:** whether retried sends count. A send that needs a 1-minute backoff already exceeds 60 seconds. The brief reads as "all accepted sends", so this plan counts them. If the intent is first-attempt latency only, the decision must be written down before the gate is measured.
- **If the gate is missed:** `password_reset` stays on the monolith. Investigate the service's queue depth, MailRelay latency and retry rate. Re-run the gate on a fresh 3-day window.

### Step 10. Cut over `password_reset`, then hold for 7 days

- **Starts when:** step 9's gate passes.
- **Data that moves:** the same as step 7, for `password_reset`. This is the most latency-sensitive type and a duplicate here is the most visible to users.
- **Dwell:** at least 3 days before the decommission gate. Then keep the old worker deployable for 7 days from the `password_reset` flip, as the brief requires.
- **Rollback, for any moved type, during these days:**
  1. Flip `notifications.route.<type>` to `monolith`. New enqueues take effect within about 10 seconds.
  2. The old worker picks up new `monolith` rows within 5 seconds.
  3. Rows already routed to the service keep flowing through the service and report status. Nothing is re-sent.
  4. Rows still `pending` in the monolith with `route = 'service'` keep being published by the publisher, which ignores flags (I5). They are sent by the service.
  5. The whole flip is well inside one minute.
- **Rollback limit:** if the service is down, rows routed to it wait. They are not lost, and the sweep pages. The plan does not re-route rows that might already be on the broker. A re-route could send them twice. Any manual recovery must first check the broker and the service inbox for that id, and that check is a human decision.
- **If it fails:** a duplicate or a missed send during this window triggers the rollback above. The old worker is still deployed, so this is possible.

### Step 11. Decommission the old worker

- **Starts when:** 7 days after the `password_reset` flip, with all three types on the service. Gate: zero `route = 'monolith' AND status = 'pending'` rows, and zero `handed_off` rows older than the 1-hour sweep threshold.
- **Changes:** remove `run_worker` and `_deliver` from the monolith. Remove the per-type flags, and enqueue always sets `route = 'service'`. Remove the monolith's copy of the templates and its MailRelay client, if nothing else uses them. Keep the `notifications` table, the publisher and the status consumer, since they are the monolith's record of each notification.
- **Changed rollback:** after this step, moving sending back to the monolith means redeploying the old worker from version control. The flag flip is no longer available. Record this in the runbook.
- **If it fails:** the old worker is removed only after the gate passes. If a row appears on the monolith route after the removal, that is a bug in step 2's routing, and the sweep catches it.

## Failure cases across the plan

| Failure | Behaviour |
| --- | --- |
| Crash after MailRelay accepts, before the outcome commit | Same key on retry. Dropped inside 24 hours. Rule I4 covers longer gaps. |
| Broker down | Enqueue still commits. Publisher and consumer wait. Sweep pages after 5 min (pending) or 1 hour (handed off). |
| MailRelay down | Retries 1, 2, 4, 8 minutes. Fifth failure: `failed`, status event, page. |
| Broker redelivery or republish | Inbox insert conflicts, and the duplicate is acked. Status update is conditional. |
| Flag store down | Enqueue falls back to `monolith`. |
| Service down during handoff | Messages wait. Rows show `handed_off`. Sweep pages. No automatic re-route. |

## Open decisions

1. **Latency gate:** do retried sends count toward the p99 under 60 seconds? (Step 9.)
2. **Render errors:** today a render error is raised before the `try`, so it escapes the batch. Proposed: treat it as a permanent failure, mark `failed` and page, without retrying. Retrying cannot fix a template error. This changes behaviour, so confirm it.
3. **Broker retention** must be at least as long as the inbox retention, which is proposed at 30 days. Confirm the broker's retention. The dedupe guarantee depends on it.
4. **Lease and timeout values:** MailRelay's timeout is not stated in the brief. The lease and the 20-hour in-doubt rule depend on it.
5. **Personal data in messages:** `email` and `payload` travel on the broker, which billing and search also use. Confirm that this is acceptable and that retention and encryption match policy.
6. **Shadow soak** (step 6) is a recommendation added by this plan, not a requirement of the brief. It adds 3 days before the first cutover.
7. **Post-decommission rollback:** confirm that a redeploy is acceptable as the only path back after step 11.
