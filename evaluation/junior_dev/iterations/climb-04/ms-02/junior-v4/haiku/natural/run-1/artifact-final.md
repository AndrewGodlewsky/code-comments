# Plan: Extract notifications into a Notification Service

## Summary

Today each monolith instance runs a sender loop every 5 seconds. Each pass claims up to 50 due rows, sends them through MailRelay, and commits all status changes at once. The loop competes with checkout for CPU and database connections, and a crash between a send and that commit causes duplicate emails.

This plan moves sending into a Notification Service with its own database. Business code does not change: it still inserts a row inside its own transaction. Each row is routed to exactly one sender when it is inserted. The three types move one at a time with a flag flip. The old sender stays deployable for 7 days after the last type moves.

## Terms

- **Notification row:** a row in the monolith `notifications` table. Every notification starts here.
- **Route:** `monolith` or `service`. It says which side sends the row. It is set at insert and never changes.
- **Route flag:** the runtime flag `notifications.route.<type>`, read in the monolith with `flags.get`. A change reaches every monolith instance within 10 seconds.
- **Type:** one of `shipping_update`, `order_confirmed`, `password_reset`.
- **Broker:** the message broker that billing and search already use. It is at-least-once. A message not acknowledged within 30 seconds is redelivered, possibly to another consumer.
- **Outbox:** a table written in the same transaction as the change it reports. A loop publishes its unpublished rows to the broker, then marks them published.
- **Inbox:** the service's `notifications` table. Its primary key is the notification id, so a repeated message does nothing.
- **Lease:** a time limit on a claimed row. Other workers skip the row until it expires.
- **Shadow copy:** a message the service renders but never sends. It checks that the service renders the same text as the monolith.
- **Shadow switch:** a runtime switch that turns on publishing of shadow copies. It stays off until rollout step 4.
- **render_hash:** SHA-256 of the rendered subject and body. Both senders compute it the same way.
- **Send window:** a send is allowed only up to 23 hours after `created_at`. MailRelay remembers idempotency keys for 24 hours, so all sends of one key fall inside one window. This limit is an addition to the brief.
- **created_at:** in the monolith, the start time of the transaction. It is slightly early, which is conservative for the latency gate and the send window.

## Data

**Monolith `notifications`, new columns and indexes:**

- `route` text, not null, default `'monolith'`. Set at insert from the route flag. Any value other than `'service'`, or a failed flag read, gives `'monolith'`.
- `shadow_sampled` boolean, default false. Set at insert to true for monolith rows where a deterministic hash of the id falls in 2 percent.
- `render_hash` and `shadow_render_hash` text. See Shadow comparison below.
- `publish_claimed_until` and `published_at`. Used by the outbox publisher.
- `completed_at`. Set by the completion consumer.
- Partial indexes on `(route, status, next_attempt_at)` and `(route, published_at)`.

**Shadow comparison.** Whichever side writes its hash second does the comparison. The old worker runs `UPDATE ... SET render_hash = ? ... RETURNING shadow_render_hash`. The completion consumer runs `UPDATE ... SET shadow_render_hash = ? ... RETURNING render_hash`. Each statement locks the row, so the second writer sees the first writer's hash. If both are set and differ, that writer alerts. A row that is never sent has no `render_hash`, so it is never compared. Parity counts only rows that have both hashes.

**Service database:**

- `notifications`: `id` (primary key, the same UUID as the monolith row), `type`, `email`, `payload`, `status` (`shadow`, `pending`, `sent`, `failed`), `attempts`, `next_attempt_at`, `lease_until`, `created_at` (copied), `received_at`, `sent_at`.
- `outbox`: completion events and shadow reports, with `published_at` and a publish lease.
- Retention: keep rows for at least the longer of the broker retention and 48 hours. The inbox must outlive any redelivery or republish.

**Topics:**

- `notifications` (monolith to service): `{schema_version, id, type, email, payload, created_at, mode: "live" | "shadow"}`.
- `notification-events` (service to monolith): completion `{id, outcome: "sent" | "failed", sent_at}`, and shadow report `{id, render_hash}`.

The service reads `notifications` with its own consumer group. The monolith reads `notification-events` with its own consumer group.

## How the system runs

Each step says what starts it, what it does, where its data lives, and what happens when it fails.

### 1. Enqueue (monolith, inside the caller's transaction)

- **Starts:** business code calls `enqueue_notification(tx, ...)` inside its own transaction. The signature does not change.
- **Does:** inserts the row as `pending`. Reads the route flag inside a try/catch that defaults to `monolith`, and sets `shadow_sampled`.
- **Data:** the monolith `notifications` table. The row exists only if the caller commits.
- **If it fails:** if the flag service is unreachable, the row is routed `monolith` and the caller's transaction still commits. If the caller rolls back, no row exists and nothing is sent.

### 2. Monolith sender (the old worker, for `route = 'monolith'` rows)

- **Starts:** the loop on each monolith instance, every 5 seconds.
- **Does:** selects due `pending` rows with `route = 'monolith'` (up to 50, `FOR UPDATE SKIP LOCKED`). Renders each row, then sends it with `idempotency_key = row id`. Writes `render_hash` and the outcome in the same UPDATE. A row older than 23 hours is marked failed and paged, and not sent. Retries follow the policy in step 3.
- **Data:** the monolith table. It commits once per batch until the per-row change in the open questions is made.
- **If it fails:** see the monolith failure rows in the table below.

### 3. Service sender (for `route = 'service'` rows)

- **Starts:** the loop on each service instance, every 5 seconds, when rows are due.
- **Does:** each row commits on its own. No transaction is held across the MailRelay call.
  1. **Claim.** In one commit, select due rows (`status = 'pending'`, `next_attempt_at <= now()`, no live lease) with `FOR UPDATE SKIP LOCKED`. Set `lease_until = now() + 2 min` and add 1 to `attempts`. Commit before sending.
  2. **Check.** If `attempts > 5` or `now() > created_at + 23h`, mark the row failed, page on-call, write the completion event, and stop. Do not send, so the customer gets no email. If `attempts > 5`, an earlier attempt may have been accepted. The page then says "outcome unknown," and on-call checks MailRelay by key and notes the result on the page.
  3. **Send.** Render with the shared template package. Call MailRelay with `idempotency_key = id`. The call timeout must be well under the 2-minute lease.
  4. **Success.** In one commit, where `status` is still `pending`: set `status = 'sent'` and `sent_at`, clear the lease, and write the completion event to the outbox. MailRelay accepted the send, so this counts as success even if the lease has expired.
  5. **Error, including timeout.** If `attempts = 5`, mark the row failed, page on-call, and write the completion event. Otherwise set `next_attempt_at = now() + BACKOFF[attempts - 1]` (1, 2, 4, 8 minutes) and clear the lease. Both writes apply only while this worker still holds its lease. If another worker has reclaimed the row, a late error changes nothing.
- **Data:** the service `notifications` table, and the completion event in the service outbox.
- **Retry policy:** each row gets at most 5 claims and so at most 5 sends. The same 5-attempt, 1/2/4/8-minute policy as today applies. One difference: a crash during a send counts as an attempt, because the claim already counted it. Today a crash does not count. This bounds crash loops. A lease that expires mid-send lets a second worker claim the row. That send uses the same key, so MailRelay should drop it (open question).
- **If it fails:** see the service failure rows in the table below.

### 4. Service inbox (consumes `notifications`)

- **Starts:** each message on the `notifications` topic.
- **Does:** in one transaction, runs `INSERT ... ON CONFLICT (id) DO NOTHING`. A live message is inserted as `pending` with `attempts = 0` and `next_attempt_at = now()`. A shadow message is inserted as `shadow`, rendered, and its shadow report is written to the outbox in the same transaction. A conflict never resets a row to `pending`. If the insert did nothing and the existing row is `sent` or `failed`, the consumer writes the completion event again, which recovers a lost event. It commits, then acknowledges. It never calls MailRelay, so it stays well inside the 30-second acknowledgement window.
- **Data:** the service `notifications` table and outbox.
- **If it fails:** a crash after insert but before the ack causes redelivery. The insert conflicts and the message is acknowledged, with no duplicate. If the service database is down, there is no ack, and the broker redelivers.

### 5. Outbox publishers (monolith and service)

- **Starts:** a loop every 5 seconds on each instance.
- **Does:** claims unpublished rows (`published_at` is null and no live `publish_claimed_until`) with a short lease, in one commit. Publishes them to the broker, then sets `published_at`. No transaction is held across the broker call. The monolith publisher claims rows where `route = 'service'`, and rows where `route = 'monolith' AND shadow_sampled` while the shadow switch is on. Each id gets only one kind, because the route is fixed at insert. The loop reads only committed rows.
- **Data:** the outbox columns. The claim lease is set before the broker call. `published_at` is set after broker confirmation.
- **If it fails:** a broker outage leaves rows unpublished, and they retry with backoff. Enqueue is unaffected, because it only inserts a row. A crash after claim lets the lease expire, and the row is published again. A crash after broker confirmation but before `published_at` causes a duplicate message, which the inbox absorbs.

### 6. Completion consumer (monolith, consumes `notification-events`)

- **Starts:** each event on the `notification-events` topic.
- **Does:**
  - Completion event: `sent` sets `status = 'sent'`, and `failed` sets `status = 'failed'`. Both set `completed_at = now()`, `WHERE id = ? AND route = 'service' AND status = 'pending'`. If no row matches, the event is a repeat or late event and changes nothing.
  - Shadow report: sets `shadow_render_hash` and compares, as described under Data.
  - It acknowledges every event.
- **Data:** the monolith `notifications` table.
- **If it fails:** no ack means redelivery. Repeated events are harmless.

### 7. Reconciler (monolith, every 5 minutes)

- **Starts:** a timer. It is idle until the first row has `route = 'service'`.
- **Does:** for each row with `route = 'service'`, `status = 'pending'`, and `published_at` older than 30 minutes:
  - If `created_at` is older than 23 hours, marks the row failed (only if still pending) and pages on-call. The service would refuse the send anyway.
  - Otherwise, republishes the message and sets `published_at = now()`, which restarts the 30-minute timer.
  - If the service is still retrying the row, the inbox finds the id and changes nothing. If the row is already terminal, the service re-emits the completion event.
- **Data:** reads and writes only the monolith database. It publishes to the broker.
- **If it fails:** if the reconciler is down, pending rows wait, and an alert watches the count of old pending service rows. If the broker is down, the republish fails and the next run retries. A lost completion event is recovered by the republish. A row is failed only once it is older than 23 hours, so the service has had repeated republishes across the whole window. A row younger than 23 hours is republished even if broker retention has passed.

### Failure summary for the monolith sender

| Failure | What happens |
|---|---|
| Crash after MailRelay accepts a send, before the batch commit | The row stays `pending`. The retry uses the same key, MailRelay drops it, and the row becomes `sent`. |
| MailRelay down or timing out | Retry as today. A timed-out send may have been accepted, and the key makes the retry safe. |
| Flag service unreachable | The row is routed `monolith`. |

## Rollout: how we build and ship it

Steps 1 to 5 happen before day 0. Shadow mode must be clean before day 0. Each step says what starts it, what data moves, where state lives, what happens when it fails, and the gate to pass.

### Step 1. Idempotency key and send window on the old worker

- **Starts:** deploy of the monolith change. No type has moved.
- **Data:** none. Each send gets `idempotency_key = row.id`. A row older than 23 hours is marked failed and paged before sending.
- **State:** the monolith table, unchanged.
- **If it fails:** a crash after acceptance is fixed by the key, as in the failure summary above. A duplicate after this step is outside the 24-hour window and needs investigation.
- **Gate:** in staging, a second send with the same key returns success without a second delivery. Confirm this with MailRelay before production. Duplicate tickets trend down.

### Step 2. Route column, flags and routing in the monolith

- **Starts:** migration, then deploy. All route flags exist and are set to `monolith`.
- **Data:** none moves. Existing rows get `route = 'monolith'` from the column default. New rows get their route from the flag at insert.
- **Changes:**
  - The old worker selects only `route = 'monolith'`. This is required before any type moves.
  - The old worker writes `render_hash` and compares it, as described under Data.
  - `enqueue_notification` keeps its signature and reads the flag with a fallback to `monolith`.
  - The outbox and shadow columns are added.
- **State:** the monolith database only.
- **If it fails:** flag errors route to `monolith`. On a large table, add the default without a rewrite and build indexes concurrently. Other failures are as in step 1.
- **Gate:** a test row with `route = 'service'` is never sent by the old worker.

### Step 3. Outbox publisher in the monolith, no traffic

- **Starts:** the publisher loop on every monolith instance. The shadow switch is off.
- **Data:** nothing is published, because no row is `service` and the shadow switch is off.
- **State:** the monolith outbox columns.
- **If it fails:** broker outage is handled as in step 5 of the system steps.
- **Gate:** zero messages published while the shadow switch is off and no row is `service`. Publish lag and error metrics feed alerts.

### Step 4. Notification Service in shadow mode

- **Starts:** deploy of the service with its own database and consumer group. Then deploy of the service outbox publisher and the monolith completion consumer. Then the shadow switch turns on, so shadow copies of `shadow_sampled` rows are published.
- **Data:** shadow messages become service rows with status `shadow`. No sends happen. Each shadow report sets `shadow_render_hash` on the monolith row.
- **Templates:** the template package is pinned to one version in both systems. Template changes for all three types are frozen during the rollout, so a rollback renders the same text.
- **State:** the service database. The service never reads the monolith database.
- **If it fails:** the inbox failures in step 4 of the system steps apply. A redelivery of a row already `sent` (after step 6) leaves the status alone, re-emits the completion event, and does not resend. MailRelay is not involved.
- **Gate:** shadow render parity is 100 percent for all three types over several days. The service handles a load test at 2x the combined peak of shipping, order and reset, with stable consumer lag. The 23-hour cutoff and dedupe-retention settings are confirmed.

### Step 5. Reconciler

- **Starts:** deploy of the monolith reconciler. It is idle until step 6.
- **Data:** the reconciler republishes or fails rows as described in step 7 of the system steps.
- **State:** the monolith database and the broker.
- **If it fails:** as in step 7 of the system steps.
- **Gate:** a staging drill stops the completion consumer for 40 minutes with live rows. After restart, every committed service row is terminal or inside its SLA in the reconciler's output, with no duplicate sends.

### Step 6. Cut over `shipping_update` (at least 3 days)

- **Starts:** set `notifications.route.shipping_update = service`. The flag reaches every monolith instance within 10 seconds.
- **Data:** new shipping rows are inserted as `service`. Existing rows do not move. Shipping rows already inserted as `monolith` drain through the old worker.
- **State:** only the `route` column of each row changes.
- **If it fails:**
  - Service down: messages wait in the broker and the service database. The consumer-lag alert fires. If the lag is sustained, roll back.
  - Broker down: the monolith outbox backs up. No rows are lost, and they publish when the broker recovers. The publish-lag alert fires.
  - MailRelay down: the service retries on the same schedule. After 5 attempts, the row is failed and paged.
  - Redelivery: absorbed by the inbox.
- **Rollback:** a flag flip to `monolith`, taking effect within 1 minute. New rows go to the old worker. Service rows keep their route and finish on the service, so nothing is lost and nothing is re-sent. Keep the service running until its pending rows and the monolith outbox backlog for this type reach zero.
- **Gate:** 3 days with zero duplicate sends in the send log, keyed by notification id. Every committed row is accounted for by reconciliation. Latency is recorded.

### Step 7. Cut over `order_confirmed` (at least 3 days)

- **Starts:** at least 3 days after step 6. Set `notifications.route.order_confirmed = service`.
- **Data, state and failures:** the same as step 6. Rollback is the same flag flip.
- **Gate:** 3 days with the step 6 checks. Before step 8 starts, the service's p99 enqueue-to-MailRelay latency on this type must be under 60 seconds. The definition is an open question.

### Step 8. Cut over `password_reset` (at least 7 days on the service)

- **Starts:** the `order_confirmed` window is at least 3 days, and its p99 is under 60 seconds. The earliest start is day 6. Set `notifications.route.password_reset = service`.
- **Data, state and failures:** the same as step 6. Alert on p99 separately during this window, not only on daily totals. Rollback is the same flag flip.
- **Latency budget:** the outbox poll (up to 5 seconds), the broker, the consumer insert, the service poll (up to 5 seconds) and MailRelay must fit under 60 seconds at p99 on normal days.
- **Gate:** at least 7 days on the service. The old worker stays deployable for this whole period.

### Step 9. Decommission the old worker (earliest day 13)

- **Starts:** `password_reset` has run on the service for 7 days, all gates in steps 6 to 8 are clean, and the drain conditions hold. Those conditions are: no `monolith` pending rows for any type, no `service` pending rows, and an empty monolith publisher backlog.
- **Actions:** remove the old worker's loop from deploy, and remove the monolith's sending path and templates. Keep the `route` column, the publisher, the completion consumer and the reconciler. The monolith `notifications` table stays as the first record and gets its own retention policy.
- **Consequence:** rollback to the monolith is no longer possible. This is a separate decision (open question).

### Timeline (earliest)

| Day | Event |
|---|---|
| 0 | `shipping_update` moves to the service |
| 3 | `order_confirmed` moves |
| 6 | `password_reset` moves, after the p99 gate |
| 13 | Old worker removed (7 days after `password_reset`) |

## Open questions

1. **MailRelay key semantics.** Confirm that the key dedupes within 24 hours, that a timed-out send counts as accepted when the key is reused, and whether the window counts from first acceptance. Everything depends on this. A lease that expires mid-send causes a second send with the same key, and the plan relies on MailRelay dropping it.
2. **23-hour send window.** This is an addition to the brief. Approve it, or give a bound that keeps every send inside MailRelay's dedupe window.
3. **p99 definition.** Should the 60-second gate include retry time? Measured with retries, a MailRelay degradation can breach the gate even when the service path is healthy. Proposed: report p99 with and without retries, and gate on the first-attempt p99 unless the business wants retries counted.
4. **Broker retention.** Confirm the broker's retention period. Service rows must outlive it and the 48-hour minimum.
5. **PII on the broker.** Messages carry email addresses and payloads. Confirm that topic encryption and access control are acceptable.
6. **Template freeze.** Confirm that the shared template package can be frozen per type for each rollout window.
7. **Rollback after decommission.** The plan treats decommission as the end of rollback. Confirm that this is acceptable.
8. **Per-row commit on the old worker.** Not needed for correctness, because the key removes the duplicate risk. Optional, to shorten batch lock time.
9. **Service instance count.** Not decided. Correctness does not depend on it. The step 4 load test should set it.
10. **Outcome-unknown rows.** When on-call finds that MailRelay accepted a send that the service marked failed, should the monolith status be corrected to `sent`? The plan leaves it `failed`, and nothing corrects it automatically.
11. **Crash counts as an attempt.** The brief says to keep today's retry policy exactly. The plan changes one thing: a crash during a send now counts toward the 5 attempts. Confirm that this change is acceptable, or ask for today's rule, in which a crash does not count.