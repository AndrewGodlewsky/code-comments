# Plan: Extract notifications into a Notification Service

## Facts the plan relies on

- MailRelay drops a `send` whose `idempotency_key` it accepted in the last 24 hours. Retries span about 15 minutes (backoff 1+2+4+8), so one key covers every retry in the policy.
- The broker is at-least-once. An unacked message is redelivered after 30 s, possibly to another consumer. A publisher's confirm means the message is stored.
- Flags reach every monolith instance within 10 s. The old worker polls every 5 s, so a flag flip takes effect within one minute.
- Today's duplicates come from committing once per batch after MailRelay has already accepted some sends.

## Invariants

- **I1. One owner per row.** `enqueue_notification` sets `route` once, to `monolith` or `service`. Only the owner sends the row. The old worker selects only `route = 'monolith' AND status = 'pending'`.
- **I2. Idempotency key.** Every MailRelay send carries `idempotency_key` = the notification id. It is set when the row is created and reused on every retry.
- **I3. Dedupe and ack.** Every consumer dedupes by notification id and acks only after its own commit. Redelivery and republish are harmless.
- **I4. No resend past the key window.** `send_started_at` is set once, on the first claim for an id, and never reset. If a claim finds an expired lease with no recorded outcome, an earlier send may have been accepted. If `send_started_at` is more than 20 hours ago, the id is marked `failed`, a status event is written, on-call is paged, and nothing is sent. The 20-hour margin sits inside MailRelay's 24-hour window.
- **I5. Flags affect only new enqueues.** The publisher, the status path and the old worker ignore flags. A rollback never moves rows that already exist.

## Schema

**Monolith `notifications`** (new columns are nullable or defaulted, so the change is metadata-only):
- `route` text, default `'monolith'`. Values: `monolith` or `service`.
- `status` gains the value `handed_off`: the service owns the row and the monolith waits for an outcome.
- `handed_off_at` timestamp.
- `shadow_published_at` timestamp (step 5 only).

**Service database** (owned only by the service):
- `inbox`: `id` (primary key, the notification id), `type`, `user_id`, `email`, `payload`, `created_at` (monolith clock), `state` (`queued`, `retry`, `sent`, `failed`), `attempts`, `next_attempt_at`, `claimed_until` (lease of the current claim; set by a claim, cleared by an outcome), `send_started_at`, `accepted_at`, `last_error`, `received_at`.
- `outbox`: terminal status events waiting for broker confirmation.
- `shadow`: one row per shadow id: `id` (primary key), the service's render hash, the monolith's `render_sha256`, and `match` (boolean).

## Message contracts

- **`notification.requested`** (monolith to service), versioned with `v`. Fields: `v`, `id`, `type`, `user_id`, `email`, `payload`, `created_at`. The payload is self-contained: rendering never reads the monolith database (step 3 checks this). `enqueue_notification` writes `id` (uuid4, as today), `user.id`, `user.email` and `payload` into the row, inside the caller's transaction. The publisher copies these fields from that row. Nothing else is read.
- **`notification.status`** (service to monolith). Terminal events only. Fields: `id`, `status` (`sent` or `failed`), `attempts`, `accepted_at` or `failed_at`, `last_error` (truncated).
- **`notification.shadow`** (monolith to service, shadow topic only). Same fields as `notification.requested`, plus `render_sha256`: the SHA-256 of the monolith's rendered subject and body, or null if rendering failed.

## Plan

Each step states what starts it, what data moves, where state lives, and what happens on failure.

### Step 1. Pass the notification id as `idempotency_key` in the old worker

- **Starts when:** the change is merged and deployed to the monolith. No flag, no schema change.
- **Data:** nothing new. `row.id` is passed to `mailrelay.send(...)` on every attempt, including retries.
- **State:** MailRelay's key store and the existing `notifications` table.
- **On failure:**
  - Crash after MailRelay accepts, before commit: the batch rolls back, the row is picked up within 5 s, and MailRelay drops the repeat.
  - MailRelay down or timing out: each timeout is a failed attempt. The next attempt reuses the key, so a send accepted despite a timeout is not doubled.
- **Verify and roll back:** duplicate-email tickets should fall toward zero. Rollback is a plain code revert. No data changes.

### Step 2. Add routing and `handed_off`, with every flag defaulting to monolith

- **Starts when:** the migration runs, then the code deploys.
- **Data:** none. Every existing row gets `route = 'monolith'`.
- **State:** monolith `notifications` (new `route` column, new status value, `handed_off_at`).
- **Changes:**
  - `enqueue_notification` keeps its signature and its insert inside the caller's transaction. It sets `route = 'service'` only when `flags.get("notifications.route.<type>") == "service"`. Anything else, including a flag read error, gives `monolith`.
  - The old worker's select adds `AND route = 'monolith'`. A test shows that a `route = 'service'` pending row is never picked up by the old worker. This enforces I1 before any row can route to the service.
- **On failure:** a flag store outage falls back to `monolith`, so checkout is never blocked. The enqueue transaction is all or nothing, as today.
- **Roll back:** revert the code. The added column and status value are harmless if left in place.

### Step 3. Check and freeze the rendering contract

- **Starts when:** a developer audit, then a PR.
- **Data:** none at runtime.
- **Work:**
  - Confirm that `templates.render` reads only its `(type, payload)` arguments. If a template reads the monolith database, add those fields to the payload at enqueue time.
  - Copy the templates into a shared package that both sides import. The monolith keeps its copy until step 11.
  - Golden tests: for sample payloads of each type, the copied templates produce byte-identical subject and body to the monolith's current output.
- **On failure:** a template that reads the database blocks cutover. Fix it here, before any service exists.

### Step 4. Build the Notification Service with its own database, receiving no traffic

- **Starts when:** the service is deployed. Nothing in the monolith points at it yet.
- **Data:** none yet.
- **State:** the service database (`inbox`, `outbox`, and `shadow` if used). Its MailRelay credentials are separate from the monolith's.
- **Components:**
  - **Consumer.** For each `notification.requested`, in one transaction: `INSERT ... ON CONFLICT (id) DO NOTHING` into `inbox` with `state = 'queued'` and `next_attempt_at = now()`. Commit, then ack. Never ack before commit.
  - **Sender.** Polls every 5 s, the same cadence as today's worker. It selects up to 50 rows with `state` in (`queued`, `retry`), `next_attempt_at <= now()`, and `claimed_until IS NULL OR claimed_until < now()`, using `FOR UPDATE SKIP LOCKED`. Each row then goes through three phases:
    1. **Claim** (short transaction, committed before the send). If `claimed_until` is not null, an earlier claim's lease expired with no outcome, so the send is in doubt. If `send_started_at` is more than 20 hours ago, apply I4: set `failed`, write the status event, page on-call, and stop. Otherwise set `claimed_until = now() + lease`, and set `send_started_at` if it is still NULL. An expired lease does not consume an attempt. The lease is longer than MailRelay's timeout plus a margin (open question 4).
    2. **Send.** Render the email, then call MailRelay with `idempotency_key = id`. The same key is used on every attempt.
    3. **Outcome** (one transaction).
       - Accepted, including when MailRelay drops a repeat under the same key: set `state = 'sent'`, `accepted_at`, clear `claimed_until`, and write the terminal status event to `outbox`.
       - Error (a render error or a MailRelay error, including timeouts): increment `attempts`, store `last_error`, clear `claimed_until`. If `attempts < 5`, set `state = 'retry'` and `next_attempt_at = now() + [1, 2, 4, 8][attempts - 1]` minutes. If `attempts = 5`, set `state = 'failed'`, write the status event to `outbox`, and page on-call.
  - **Outbox loop.** Publishes unconfirmed `outbox` rows and marks each one published only after the broker confirms. Pages on-call if a row stays unpublished for more than 5 minutes.
  - **Shadow consumer** (if used). For each `notification.shadow`, renders with the shared templates and inserts one `shadow` row keyed by id: its own render hash, the message's `render_sha256`, and `match`. Duplicates conflict on id and are acked. It never calls MailRelay. Startup fails if shadow mode and a MailRelay client are both enabled.
- **On failure:**
  - Crash between MailRelay accepting and the outcome commit: the lease expires and the row is reclaimed. The claim finds the send in doubt and, within 20 hours of `send_started_at`, sends again with the same key. MailRelay drops it. The crash does not consume an attempt.
  - Broker down: the consumer waits and reconnects. Nothing is acked, so nothing is lost.
  - MailRelay down: the retry and failure rules above apply. The fifth failure marks the row `failed` and pages.
  - Redelivery: the insert conflicts, the duplicate is acked, and the existing row is not touched.

### Step 5. Monolith handoff: publisher, status consumer, shadow publishing

- **Starts when:** the monolith deploys these background loops. Still no row is routed to the service.
- **Data and work:**
  - **Publisher.** Every 5 s, selects up to 50 `route = 'service' AND status = 'pending'` ids, oldest first, and handles them one at a time. Each row gets its own short transaction: lock it with `FOR UPDATE SKIP LOCKED`, repeating the route and status checks in the lock query, so a row another instance has already handed off is skipped. Publish `notification.requested` with a bounded confirm timeout (open question 4), set `status = 'handed_off'` and `handed_off_at`, and commit. On a timeout or error, roll back. The row stays `pending` and the next poll tries again.
  - **Status consumer.** Applies `notification.status` with `UPDATE notifications SET status, attempts WHERE id = ? AND status IN ('pending', 'handed_off')`, and acks after commit. It stores only `status` and `attempts`. `accepted_at` and `last_error` stay in the event and the service inbox.
  - **Shadow publisher** (optional, recommended). Covers every row created after a fixed shadow start time (a config value, set at deploy), of any route and any type, including rows the monolith sends itself. This lets step 6 check all three types before `shipping_update` moves. For each such row with `shadow_published_at IS NULL`, it renders with the monolith's templates, computes `render_sha256` (null if rendering fails), publishes `notification.shadow`, then stamps `shadow_published_at`. Shadow messages never change a row's status. A crash between publishing and stamping publishes again, and the service dedupes on id.
- **State:** monolith `notifications` for the handoff state. The broker for messages in flight.
- **Sweep** (every minute, never resends). Pages on-call when a `route = 'service'` row is still `pending` after 5 minutes, or a row has been `handed_off` for more than 1 hour without a status event.
- **On failure:**
  - Publisher crashes after broker confirm, before commit: the row stays `pending` and is published again. The service dedupes on id. No duplicate send.
  - Broker down or confirm timeout: rollback, and the row stays `pending`. Enqueue still succeeds, because it writes only to the database. The sweep pages after 5 minutes.
  - Status event arrives before the publisher commits: the publisher's row lock makes the status update wait. After a commit the row is `handed_off` and the update matches. After a rollback (the broker stored the message but the confirm was lost) the row is `pending`, the update still matches, and the row becomes `sent` or `failed`, so the publisher never publishes it again.
  - Status redelivery: the conditional update matches nothing. No-op.
  - Status event lost before the broker confirmed it: the outbox loop retries, and the service pages after 5 minutes. A confirmed event is redelivered until acked. Anything still missing is caught by the 1-hour sweep.
  - Service down: messages wait in the broker and rows stay `handed_off`. The sweep pages after 1 hour.

### Step 6. Shadow soak and parity check

- **Starts when:** step 5 is live with the shadow publisher on.
- **Data:** every notification is rendered twice, once by the monolith (shadow publisher) and once by the service (shadow consumer). Each pair is recorded in the service's `shadow` table.
- **Parity:** a mismatch is a row with `match = false`. That means the hashes differ, or either side is null.
- **Gate to leave (recommended, not in the brief):** at least 3 days with zero mismatches, and shadow queue depth bounded at peak load.
- **On failure:** a mismatch blocks cutover. Fix the templates or the payload contract, then return to step 3. Shadow copies cannot send mail, so no user is affected.

### Step 7. Cut over `shipping_update`

- **Starts when:** steps 1 to 6 are complete and the sweep alerts have been confirmed to fire in a test.
- **Data:** new `shipping_update` enqueues get `route = 'service'`. Each row goes publisher, then service, then status back to the monolith.
- **State:** the monolith row goes `pending`, then `handed_off`, then `sent` or `failed`, with `attempts` copied from the event. The service inbox holds the send, `accepted_at` and `last_error`.
- **Rows in flight:** rows routed to the monolith before the flip are sent by the old worker. Rows routed after the flip are sent by the service. The route is fixed per row (I1), so the two paths never overlap.
- **Dwell:** at least 3 days. Watch the sweep alerts, MailRelay duplicate-key drops, support duplicate tickets, and retry and failure rates.
- **On failure:** flip the flag back (step 10).

### Step 8. Cut over `order_confirmed`

- **Starts when:** step 7 has run at least 3 days with no unresolved sweep pages or duplicate reports.
- **Data:** as in step 7. Checkout's cost is unchanged: the enqueue path adds only a flag read and a column value. The publisher runs off the checkout path.
- **Dwell:** at least 3 days. This window is the measurement window for the latency gate in step 9.
- **On failure:** roll back this type only. `shipping_update` stays on the service.

### Step 9. Latency gate before `password_reset`

- **Starts when:** step 8's dwell is complete.
- **Measure:** on the service, for accepted `order_confirmed` sends, `latency = accepted_at − created_at`. `created_at` comes from the monolith's database clock, so check clock skew between the two hosts first. p99 must be under 60 s.
- **Retried sends count.** The brief reads as "all accepted sends", so this plan counts them. A send that needs a 1-minute backoff already exceeds 60 s. If the intent is first-attempt latency only, record that before the gate is measured (open question 1).
- **On failure:** `password_reset` stays on the monolith. Investigate the service's queue depth, MailRelay latency and retry rate, then re-run the gate on a fresh 3-day window.

### Step 10. Cut over `password_reset`, then hold

- **Starts when:** step 9's gate passes.
- **Data:** as in step 7. This is the most latency-sensitive type, and a duplicate here is the most visible to users.
- **Dwell:** the old worker stays deployable for 7 days from this flip, as the brief requires. Decommission waits for that.
- **Rollback, for any moved type, during those days:**
  1. Flip `notifications.route.<type>` to `monolith`. New enqueues take effect within about 10 s.
  2. The old worker picks up new `monolith` rows within 5 s.
  3. Rows already routed to the service keep flowing and report status. Nothing is re-sent.
  4. Rows still `pending` with `route = 'service'` keep being published by the publisher, which ignores flags (I5). The service sends them.

  The whole flip is well inside one minute.
- **Rollback limit:** if the service is down, routed rows wait. They are not lost, and the sweep pages. The plan never re-routes a row that might already be on the broker, because that could send it twice. Any manual recovery must first check the broker and the service inbox for that id. That check is a human decision.

### Step 11. Decommission the old worker

- **Starts when:** 7 days after the `password_reset` flip, with all three types on the service. Gate: zero `route = 'monolith' AND status = 'pending'` rows, and zero `handed_off` rows older than the 1-hour sweep threshold.
- **Changes:** remove `run_worker` and `_deliver` from the monolith. Remove the per-type flags, so enqueue always sets `route = 'service'`. Remove the monolith's copy of the templates and its MailRelay client, if nothing else uses them. Keep the `notifications` table, the publisher and the status consumer, since they are the monolith's record of each notification.
- **Rollback after this step:** a redeploy of the old worker from version control. The flag flip is no longer available. Record this in the runbook (open question 7).
- **On failure:** if a row appears on the monolith route after removal, that is a bug in step 2's routing, and the sweep catches it.

## Open questions

1. **Latency gate:** do retried sends count toward the p99 under 60 s? (Step 9.)
2. **Render errors:** the plan counts a render error as a failed attempt, with the same 5 attempts, backoff and page as a MailRelay error. This keeps the brief's retry policy. Failing at once would be faster but changes that policy. Confirm.
3. **Broker retention:** must be at least as long as inbox retention, proposed at 30 days. Confirm the broker's retention, because the dedupe guarantee depends on it.
4. **Timeouts and leases:** MailRelay's timeout and the broker confirm timeout are not in the brief. The sender lease, the publisher's confirm timeout and the 20-hour in-doubt rule depend on them.
5. **Personal data:** `email` and `payload` travel on the broker, which billing and search also use. Confirm that this is acceptable and that retention and encryption match policy.
6. **Shadow soak:** step 6 is this plan's recommendation, not the brief's requirement. It adds 3 days before the first cutover. Confirm.
7. **Post-decommission rollback:** confirm that a redeploy is acceptable as the only path back after step 11.
8. **Flag tooling and owner:** the brief does not say which tool sets `notifications.route.<type>` or who may flip it. The runbook must name both before step 7.
9. **Reclaim limit:** a row that crashes the sender before MailRelay is called is reclaimed without limit, bounded only by the 20-hour rule. Decide whether to cap reclaims.