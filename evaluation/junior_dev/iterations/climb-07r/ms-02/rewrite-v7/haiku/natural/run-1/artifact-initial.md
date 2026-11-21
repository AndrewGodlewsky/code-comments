# Plan: Extract Notifications into a Notification Service

## Assumptions

- The database is Postgres. The existing SQL uses `now()` and `FOR UPDATE SKIP LOCKED`.
- The broker is the existing at-least-once broker. Its name and retention are not given in the brief, so they are an open question below.
- The monolith's `notifications` table stays the first and authoritative record. Callers keep calling `enqueue_notification(tx, ...)`.

## Core mechanisms

These five mechanisms carry every invariant. The steps below build them one at a time.

1. **Route stamp at enqueue.** `enqueue_notification` writes `route` ('monolith' or 'service') into the same row, inside the caller's transaction, using the per-type flag. Only the side named by the stamp ever sends that row. Flag propagation skew (up to 10 s) therefore cannot cause a double send: a row's sender is fixed once, at insert time.
2. **Outbox relay in the monolith.** A relay publishes `route = 'service'` rows to the broker. It never calls MailRelay. Publishing is at-least-once, so the relay can repeat a message.
3. **Inbox in the service.** The service's `notifications` table is keyed by `notification_id`. An insert that conflicts means the message was already seen, so the service only re-emits its receipt. This absorbs broker redelivery and relay republish.
4. **Idempotency key.** Every MailRelay send uses `idempotency_key = notification_id`. A retry or a re-run after a crash is dropped by MailRelay within 24 h, and the retry window is only about 15 minutes.
5. **Receipts.** The service emits `received`, `sent` and `failed` events back to the broker. The monolith uses `received` to find rows the service never got and republishes them. This closes the "nothing lost" loop without relying on broker retention.

## Where state lives

| State | Location | Owner |
|---|---|---|
| Notification record, route stamp, publish and receipt times, mirrored final status | Monolith `notifications` | Monolith |
| Flags `notif.route.<type>` | Flag store (`flags.get`) | Platform |
| Messages in transit | Broker | Platform |
| Inbox, render output, attempts, lease, paging state | Service DB `notifications` | Notification Service |
| Accepted sends and idempotency keys (24 h) | MailRelay | MailRelay |

**Message from monolith to service:** `{notification_id, type, user_id, email, payload, enqueued_at}`. `enqueued_at` is the monolith row's `created_at`. The payload must carry everything the templates need, because the service cannot read the monolith database.

**Event from service to monolith:** `{notification_id, event: received | sent | failed, at}`.

**Service table `notifications`:** the monolith's columns plus `lease_until`, `sent_at`, `failed_at`, `paged_at` and `received_at`.

---

## Step 1: Idempotency key on the old worker

- **Starts when:** a normal deploy, before any other step. This is the first change shipped.
- **Data moves:** nothing new. `mailrelay.send(..., idempotency_key=str(row.id))`.
- **State:** none new. The key is held by MailRelay for 24 h.
- **On failure:**
  - If the key is rejected or errors, the send fails like any other `mailrelay.Error`, and the existing retry policy applies. Roll back the deploy.
  - If the worker crashes after MailRelay accepts part of a batch, the rows stay `pending` and are re-sent with the same key. MailRelay drops them and returns success, so the duplicate is prevented. This is the case behind the roughly 30 duplicate emails a week.
  - Verify by tracking the duplicate count from support, which should fall.

## Step 2: Schema and flags, with no behaviour change

- **Starts when:** deploy the migration, then the code.
- **Data moves:** none.
- **Changes:**
  - Add `route text NOT NULL DEFAULT 'monolith'`, `published_at timestamptz NULL` and `receipt_at timestamptz NULL` to `notifications`. A constant default is metadata-only on Postgres 11 and later.
  - Define flags `notif.route.shipping_update`, `notif.route.order_confirmed` and `notif.route.password_reset`, all defaulting to `monolith`.
  - `enqueue_notification` reads the flag for its type and writes `route`. Read flags once per process and cache them, to keep caller transactions free of extra latency.
- **State:** monolith DB only. Existing pending rows get `'monolith'` from the default, so the old worker keeps them.
- **On failure:**
  - If the flag store is unreachable, stamp `'monolith'`. That is the safe default: it is the current behaviour.
  - During a rolling deploy, old instances omit `route`, which takes the default `'monolith'`. That is also safe.
  - Rollback: revert the code. The column and flags are harmless to leave in place.

## Step 3: Build the Notification Service, with no production traffic

- **Starts when:** the service's own pipeline deploys. Nothing in the monolith changes.
- **Data moves:** none in production. Test messages go to a non-production queue or topic.
- **Contents:**
  - A consumer that inserts into the inbox and acknowledges after commit.
  - Rendering, moved from `templates.render`.
  - A sender with the existing retry policy: 5 attempts, backoff of 1, 2, 4 and 8 minutes, then `failed` and page. Send with `idempotency_key = notification_id`.
  - A receipt publisher.
- **State:** the service DB only.
- **On failure:** with no production traffic, failures are test failures. Acceptance tests:
  - A duplicate message produces one send.
  - A crash after MailRelay accepts, followed by a restart, produces one email. This needs a fake MailRelay that honours keys.
  - A redelivered message that arrives after commit but before ack is acknowledged without a second insert.

## Step 4: Monolith outbox relay and receipt consumer

- **Starts when:** deploy to every monolith instance. The relay selects nothing until step 6, so it is inert.
- **Data moves:**
  - **Relay:** select rows where `route = 'service'` and either `published_at IS NULL` or the receipt is overdue. The overdue threshold is 5 minutes. Publish the message, wait for broker confirmation, then set `published_at`. Select with `FOR UPDATE SKIP LOCKED`. Commit per row or per small batch.
  - **Receipt consumer:** on `received`, set `receipt_at`. On `sent` or `failed`, move `status` forward from `pending` to `sent` or `failed`, and set `receipt_at` if it is still null.
- **State:** monolith `notifications`, plus the broker.
- **On failure:**
  - Broker down: rows stay unpublished. The relay retries on the next poll, and the rows are safe in the monolith DB.
  - Crash after broker confirmation but before `published_at` is set: the row is republished. The service dedupes it by inbox key.
  - Receipt lost: the overdue check republishes it. The service re-emits `received` for a message it already has.
  - Receipt consumer redelivery: updates are idempotent and monotonic, so a repeat is harmless.
  - A row still without a receipt after 30 minutes raises an alert, to catch a service or broker problem before it becomes a loss.

## Step 5: Load and failure rehearsal in staging

- **Starts when:** steps 3 and 4 are deployed. This is a gate, not a data change.
- **Data moves:** synthetic traffic at about 53,500 messages a day, which is shipping_update plus order_confirmed. Test at 3 times that rate as a peak.
- **State:** staging DBs and the test broker.
- **Failure injection:**
  - MailRelay down: the retry schedule runs, then pages.
  - Broker down: rows stay in the monolith and drain on recovery.
  - Kill the service mid-send: the lease expires and the row is re-sent with the same key.
  - Kill the monolith relay after confirmation: duplicates are absorbed.
  - Redeliver messages: no double sends.
- **Exit:** the service can keep up with peak, and no injected failure loses a row or sends a duplicate.

## Step 6: Cutover of shipping_update

- **Starts when:** step 5 passes. An operator flips `notif.route.shipping_update` to `service`.
- **Data moves:** new shipping_update rows are stamped `service`. The relay publishes them. The service sends them. Rows stamped `monolith` before the flip keep draining through the old worker.
- **State:** `route` on each row. Each row keeps one stamp for life.
- **On failure:**
  - Rows stamped `service` that are unpublished wait in the monolith DB until the relay recovers. Nothing is lost.
  - Service failures follow the retry policy and end in `failed` with a page.
  - Rollback is covered in its own section below.
- **Bake:** at least 3 days. Exit when there are zero duplicate sends, no row older than 15 minutes without a receipt, and every `failed` row has been paged and reviewed.

## Step 7: Cutover of order_confirmed

- **Starts when:** shipping_update has been on the service for at least 3 days and passed its exit check.
- **Data moves and state:** as in step 6, for `order_confirmed`.
- **Bake:** at least 3 days. Record the enqueue-to-MailRelay latency for each sent row as `sent_at - enqueued_at`. Use 12,000 a day as the sample size.
- **On failure:** as in step 6. Rollback is covered below.

## Step 8: Latency gate, with no data movement

- **Starts when:** the order_confirmed bake is complete.
- **Check:** the p99 of enqueue-to-MailRelay latency on order_confirmed must be under 60 s over the bake window.
- **On failure:** do not start step 9. Investigate relay lag, service queue depth and MailRelay response time. Fix, then re-measure over a new bake window.
- **Note:** `enqueued_at` comes from the monolith clock and `sent_at` from the service clock. Both must be NTP-synced, or the latency figure is biased. See the open questions.

## Step 9: Cutover of password_reset

- **Starts when:** step 8 passes.
- **Data moves and state:** as in step 6, for `password_reset`.
- **Extra care:** the payload includes the reset link or token. It now sits in the broker and in the service DB. Apply the retention decision in the open questions, such as clearing the payload after the send completes.
- **Clock:** the 7-day decommission clock starts from the moment this flag flips.
- **Old worker:** keep it deployable for the whole period. Rollback depends on it.

## Step 10: Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days.
- **Preconditions:**
  - Zero `monolith`-stamped rows are `pending`.
  - All three flags read `service`.
- **Data moves:** none.
- **Changes:**
  - Remove `run_worker`, `_deliver` and the monolith copy of the templates.
  - Keep the relay and the receipt consumer. They are the permanent outbox and status path.
  - Replace the flag check with a constant `service` stamp, or retire the flags once they are no longer needed.
- **State:** the monolith `notifications` table stays as the audit record.
- **On failure:** after this step, rollback to the monolith is no longer possible. That is the point of decommission, so confirm the preconditions first.

---

## Rollback of a type

Use this for any type before step 10. It is a flag flip.

1. Set `notif.route.<type>` to `monolith`.
2. Within about 10 s, new enqueues are stamped `monolith`. The old worker, already running, picks them up within `POLL_SECONDS` (5 s). Total time is under a minute.
3. Rows already stamped `service` keep going. The relay finishes publishing and republishing them until they have a receipt. The service sends or fails each one. Nothing is re-sent, because each row has one stamp and only the side named by the stamp acts on it.
4. The service consumer keeps running during rollback until its backlog for that type is drained. Do not stop it.
5. The old worker filters on `route = 'monolith'`, so it never picks up a service-stamped row.

## Failure summary

| Failure | Behaviour | Loss or duplicate? |
|---|---|---|
| Crash in monolith relay after broker confirmation | Republished. Service inbox dedupes. | No loss, no duplicate sent |
| Broker down | Rows wait in monolith DB. Relay retries. | No loss |
| Broker redelivers a message | Inbox insert conflicts. Receipt re-emitted. | No duplicate |
| Lost receipt | Relay republishes after 5 min. Service re-emits receipt. | No loss |
| Service crash mid-send | Lease expires. Re-send with same key. MailRelay drops it if already accepted. | No duplicate (within the 24 h key window) |
| MailRelay down | Backoff 1, 2, 4, 8 min. Then `failed` and page. | Failed and paged, not lost |
| Page itself fails | Row is `failed` with `paged_at` null. A sweeper retries the page. | Not lost |
| Service DB down | Consumer does not ack. Broker redelivers after 30 s. | No loss |
| Monolith DB down | Caller's transaction fails, as today. | No row, so nothing to lose |

## Open questions and decisions needed

1. **Broker name, topology and retention.** Retention need not cover the worst outage, because the receipt loop republishes from the monolith. It should still be stated.
2. **MailRelay.** Is there a sandbox for staging? What happens if two sends with the same key are in flight at once? Lease length must exceed the MailRelay timeout plus a margin, which avoids the race in practice but does not prove it safe. Can a dropped duplicate be told apart from a first send, for metrics?
3. **Render errors.** Today a render exception aborts the whole batch, and the row is retried on every poll indefinitely. Proposal: a render failure counts as an attempt, so it reaches `failed` and pages. This is a change to the retry policy and needs sign-off.
4. **Paging failures.** The `paged_at` sweeper in the failure table needs an owner.
5. **PII and secrets.** Email addresses and reset tokens will sit in the broker and the service DB. Decide encryption at rest, the broker's access controls, and how long payloads are kept.
6. **Latency clocks.** Decide whether monolith and service clocks are NTP-synced enough for the p99 gate, or whether to measure on one clock.
7. **Peak load.** The brief gives daily totals. Confirm peak per-second rates before step 5.
8. **Monolith status for service rows.** This plan mirrors status back for support. Confirm that support tooling reads that mirror, rather than the service's table.