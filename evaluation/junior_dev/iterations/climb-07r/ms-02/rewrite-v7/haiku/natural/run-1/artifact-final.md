# Plan: Extract Notifications into a Notification Service

## Summary

Today, a worker inside the monolith sends notification emails, and that work competes with checkout for CPU and database connections. This plan moves sending into a separate Notification Service with its own database. Callers still write a notification row inside their own transaction. A relay copies the rows that belong to the service onto the message broker. The service sends them through MailRelay and reports back, so the monolith row always shows what happened. Each notification type moves over alone, and any type can move back by a flag flip.

## Assumptions

- The database is Postgres. The existing SQL uses `now()` and `FOR UPDATE SKIP LOCKED`.
- The broker is the existing at-least-once broker. Its name and retention are not known yet (open question 1).
- The monolith's `notifications` table stays the first and authoritative record.

## Terms

- **Notification:** one email to one user. It is one row in the monolith's `notifications` table.
- **Types:** `shipping_update` (a carrier webhook updates a shipment, about 40,000 a day), `order_confirmed` (checkout commits an order, about 12,000 a day) and `password_reset` (a user asks to reset a password, about 1,500 a day). All three are email only, sent through MailRelay.
- **MailRelay:** the outside email provider. Its `send()` takes an optional `idempotency_key`. If it has already accepted a send with the same key in the last 24 hours, it drops the new send and reports success. Today the monolith passes no key.
- **Idempotency key:** a value that lets MailRelay recognise a repeat send. Every send uses the notification's id.
- **Broker:** the message queue that billing and search also use. It is at-least-once. A message not acknowledged within 30 seconds is redelivered, possibly to a different consumer. A publisher gets a confirmation once a message is stored.
- **Ack (acknowledge):** the consumer tells the broker it finished a message, so the broker stops redelivering it.
- **Relay:** a loop in the monolith that copies service-bound rows to the broker.
- **Inbox:** the service's `notifications` table, keyed by notification id. A row there means the service already has that message.
- **Route:** a column on each monolith row that says which side sends it: `monolith` or `service`. It is set once, when the row is inserted.
- **Flag:** a runtime setting read with `flags.get(name)`. A change reaches every monolith instance within 10 seconds.
- **Lease:** a time-limited claim on a row. While the lease runs, no other sender takes that row. When it expires, another sender may take it.
- **Receipt:** an event the service sends back to the monolith: `received`, `sent` or `failed`.
- **Page on-call:** `alerts.page_oncall(...)`, which alerts the engineer on duty.
- **Bake:** the period a type runs on the service before the next type moves.
- **p99 latency:** the time within which 99% of sends finish.
- **NTP:** the protocol that keeps server clocks in step.

## How the system works

### Rules that hold everywhere

- Callers do not change. Business code keeps calling `enqueue_notification(tx, ...)` inside its own transaction. The row exists only if that transaction commits.
- The service never reads or writes the monolith database. The monolith never touches the service database. The broker is the only channel between them.
- Every committed notification ends in one of two states: accepted by MailRelay, or marked failed with on-call paged.
- No user gets the same notification twice. This holds after a crash, after broker redelivery, and during cutover or rollback.
- Every send passes the notification id as the idempotency key. This is done on the old worker too, before any type moves.
- Retry policy is the same on either side. There are 5 attempts. The wait before attempts 2, 3, 4 and 5 is 1, 2, 4 and 8 minutes. After the fifth failure the row is marked failed and on-call is paged. A timeout counts as a failure.
- Template rendering moves into the service.

### Route stamp at enqueue

`enqueue_notification` reads the flag for its type and writes `route` into the same row, inside the caller's transaction. The flag is cached for a few seconds, so caller transactions do not wait on the flag store. If the flag store is unreachable, the stamp is `monolith`. Only the side named by the stamp ever sends a row. Because the stamp is fixed at insert, a flag change that reaches instances at different times cannot make both sides send the same row.

### Outbox relay in the monolith

The relay publishes `service` rows to the broker. It never calls MailRelay. Publishing is at-least-once, so the relay can repeat a message. The service's inbox absorbs the repeat.

### Inbox and idempotency in the service

The service's inbox is keyed by `notification_id`. If an insert conflicts, the message was already seen, so the service only re-emits its receipt. This absorbs both broker redelivery and relay republishing. Every MailRelay send uses `idempotency_key = notification_id`. A retry, or a re-run after a crash, is dropped by MailRelay within 24 hours. The whole retry schedule takes about 15 minutes, well inside that window.

### Receipts

The service sends `received`, `sent` and `failed` events back to the broker. The monolith uses `received` to find rows the service never got, and it republishes those rows. This closes the "nothing lost" loop without relying on broker retention.

### Where state lives

| State | Location | Owner |
|---|---|---|
| Notification record, route stamp, publish and receipt times, mirrored status | Monolith `notifications` | Monolith |
| Flags `notif.route.<type>` | Flag store (`flags.get`) | Platform |
| Messages in transit | Broker | Platform |
| Inbox, rendered output, attempts, lease, paging state | Service DB `notifications` | Notification Service |
| Accepted sends and idempotency keys (24 hours) | MailRelay | MailRelay |

### Messages

- **Monolith to service:** `{notification_id, type, user_id, email, payload, enqueued_at}`. `enqueued_at` is the monolith row's `created_at`. The payload must hold everything the templates need, because the service cannot read the monolith database.
- **Service to monolith:** `{notification_id, event: received | sent | failed, at}`.
- **Monolith columns added:** `route`, `published_at` and `receipt_at`.
- **Service `notifications` table:** the monolith's columns, plus `lease_until`, `sent_at`, `failed_at`, `paged_at` and `received_at`.

## Shipping steps

Steps are in the order they ship. Each one says what starts it, what data moves, where the state lives, and what happens when something goes wrong. The failure table below covers crashes, broker outages, MailRelay outages and redelivery for the whole system.

### Step 1: Idempotency key on the old worker

- **Starts when:** a normal deploy. This is the first change shipped.
- **Data moves:** nothing new. The worker calls `mailrelay.send(..., idempotency_key=str(row.id))`.
- **State:** none new. MailRelay holds each key for 24 hours.
- **On failure:**
  - If MailRelay rejects the key or errors, the send fails like any other error and the retry policy applies. Roll back the deploy.
  - If the worker crashes after MailRelay accepts part of a batch, the rows stay `pending` and are sent again with the same key. MailRelay drops them. This is the cause of about 30 duplicate emails a week.
  - Verify by checking that support's duplicate count falls.

### Step 2: Schema and flags, with no behaviour change

- **Starts when:** the migration deploys first, then the code.
- **Data moves:** none.
- **Changes:**
  - Add `route text NOT NULL DEFAULT 'monolith'`, `published_at timestamptz NULL` and `receipt_at timestamptz NULL` to the monolith `notifications` table. A constant default is metadata-only on Postgres 11 and later.
  - Define the flags `notif.route.shipping_update`, `notif.route.order_confirmed` and `notif.route.password_reset`. All default to `monolith`.
  - `enqueue_notification` reads its type's flag and writes `route`, as described above.
  - The old worker's select adds `AND route = 'monolith'`, so it never sends a row stamped `service`. Without this filter, the old worker would send service rows too, which would cause duplicates.
- **State:** monolith database only. Existing pending rows get `monolith` from the default, so the old worker keeps them.
- **On failure:**
  - Flag store unreachable: stamp `monolith`, which is the current behaviour.
  - Rolling deploy: old instances omit `route`, which takes the default `monolith`. This is also safe.
  - Rollback: revert the code. The column and flags can stay.

### Step 3: Build the Notification Service, with no production traffic

- **Starts when:** the service's own pipeline deploys. Nothing in the monolith changes.
- **Data moves:** none in production. Test messages go to a non-production queue or topic.
- **Contents:**
  - A consumer that inserts each message into the inbox, publishes `received` after the insert commits, and acks only after commit.
  - Rendering, moved from `templates.render`.
  - A sender with the retry policy above. It claims each row with a lease, and the lease must outlast the MailRelay timeout plus a margin. It sends with `idempotency_key = notification_id`. After the fifth failure it marks the row `failed` and pages.
  - A receipt publisher for `received`, `sent` and `failed`.
- **State:** the service database only.
- **On failure:** with no production traffic, failures are test failures. The acceptance tests are:
  1. A duplicate message produces one send.
  2. A crash after MailRelay accepts a send, followed by a restart, produces one email. This needs a fake MailRelay that honours keys.
  3. A redelivered message that arrives after commit but before ack is acked without a second insert.

### Step 4: Monolith relay and receipt consumer

- **Starts when:** deploy to every monolith instance. The relay selects nothing until step 6 stamps rows `service`, so it is inert until then.
- **Data moves:**
  - **Relay:** selects rows with `route = 'service'` where `published_at` is null, or where `published_at` is more than 5 minutes ago and `receipt_at` is still null. It selects with `FOR UPDATE SKIP LOCKED`, publishes the message, waits for broker confirmation, then sets `published_at`. It commits per row or per small batch.
  - **Receipt consumer:** on `received`, sets `receipt_at`. On `sent` or `failed`, moves `status` forward from `pending` to `sent` or `failed`, and sets `receipt_at` if it is still null.
- **State:** the monolith `notifications` table, plus the broker.
- **On failure:**
  - Broker down: rows stay unpublished. The relay retries on the next poll. The rows are safe in the monolith database.
  - Crash after broker confirmation but before `published_at` is set: the row is republished. The service dedupes it by inbox key.
  - Lost receipt: the overdue check republishes the row, and the service re-emits `received` for a message it already has.
  - Receipt redelivered: updates are idempotent and monotonic, so a repeat is harmless.
  - A row still without a receipt after 30 minutes raises an alert. This catches a service or broker problem before it becomes a loss.

### Step 5: Load and failure rehearsal in staging

- **Starts when:** steps 3 and 4 are deployed. This is a gate. No data changes.
- **Data moves:** synthetic traffic of about 53,500 messages a day, which is `shipping_update` plus `order_confirmed`. Test at 3 times that rate as a peak. Confirm the real per-second peak first (open question 7).
- **State:** staging databases and the test broker.
- **Failure injection:**
  - MailRelay down: the retry schedule runs, then pages.
  - Broker down: rows stay in the monolith and drain on recovery.
  - Service killed mid-send: the lease expires and the row is re-sent with the same key.
  - Monolith relay killed after confirmation: duplicates are absorbed.
  - Messages redelivered: no double sends.
- **Exit:** the service keeps up with peak, and no injected failure loses a row or sends a duplicate.

### Step 6: Cutover of shipping_update

- **Starts when:** step 5 passes. An operator sets `notif.route.shipping_update` to `service`.
- **Data moves:** new `shipping_update` rows are stamped `service`. The relay publishes them, and the service sends them. Rows stamped `monolith` before the flip keep draining through the old worker.
- **State:** the `route` column on each row. Each row keeps one stamp for its whole life.
- **On failure:**
  - Service-stamped rows that are not yet published wait in the monolith database until the relay recovers. Nothing is lost.
  - Service failures follow the retry policy and end in `failed` with a page.
  - Rollback is covered in its own section below.
- **Bake:** at least 3 days. Exit when there are zero duplicate sends, no row older than 15 minutes without a receipt, and every `failed` row has been paged and reviewed.

### Step 7: Cutover of order_confirmed

- **Starts when:** `shipping_update` has run on the service for at least 3 days and passed its exit check.
- **Data moves and state:** as in step 6, for `order_confirmed`.
- **Bake:** at least 3 days. For each sent row, record the enqueue-to-MailRelay latency as `sent_at - enqueued_at`. Expect about 12,000 rows a day as the sample.
- **On failure:** as in step 6.

### Step 8: Latency gate

- **Starts when:** the `order_confirmed` bake is complete. No data moves.
- **Check:** the p99 of enqueue-to-MailRelay latency on `order_confirmed` must be under 60 seconds over the bake window.
- **On failure:** do not start step 9. Investigate relay lag, service queue depth and MailRelay response time. Fix the cause, then re-measure over a new bake window.
- **Note:** `enqueued_at` comes from the monolith clock and `sent_at` from the service clock. Both must be NTP-synced, or the latency figure is biased (open question 6).

### Step 9: Cutover of password_reset

- **Starts when:** step 8 passes.
- **Data moves and state:** as in step 6, for `password_reset`.
- **Extra care:** the payload includes the reset link or token. It now sits in the broker and in the service database. Apply the retention decision from open question 5, such as clearing the payload after the send completes.
- **Clock:** the 7-day decommission clock starts when this flag flips.
- **Old worker:** stays deployable for the whole period. Rollback depends on it.

### Step 10: Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days.
- **Preconditions:** zero `monolith`-stamped rows are `pending`, and all three flags read `service`.
- **Data moves:** none.
- **Changes:**
  - Remove `run_worker`, `_deliver` and the monolith copy of the templates.
  - Keep the relay and the receipt consumer. They are the permanent outbox and status path.
  - Replace the flag check with a constant `service` stamp, or retire the flags.
- **State:** the monolith `notifications` table stays as the audit record.
- **On failure:** after this step, rollback to the monolith is no longer possible. That is the point of decommissioning, so confirm the preconditions first.

## Rollback of a type

Use this for any type before step 10. It is a flag flip.

1. Set `notif.route.<type>` to `monolith`.
2. Within about 10 seconds, new enqueues are stamped `monolith`. The old worker, already running, picks them up within `POLL_SECONDS` (5 seconds). The total time is under a minute.
3. Rows already stamped `service` keep going. The relay finishes publishing and republishing them until each has a receipt. The service sends or fails each one. Nothing is re-sent, because each row has one stamp and only the side named by the stamp acts on it.
4. The service consumer keeps running during rollback until its backlog for that type is drained. Do not stop it.
5. The old worker filters on `route = 'monolith'` (added in step 2), so it never picks up a service-stamped row.

## What happens when things fail

| Failure | What happens | Loss or duplicate? |
|---|---|---|
| Old worker crashes after MailRelay accepts part of a batch | Before step 1: rows are re-sent and duplicates occur (about 30 a week). After step 1: re-sent with the same key, and MailRelay drops them. | Before step 1: duplicates. After step 1: no duplicate within 24 hours. |
| Monolith relay crashes after broker confirmation | Row is republished. Service inbox dedupes it. | No loss, no duplicate sent |
| Broker down | Rows wait in the monolith database. The relay retries. | No loss |
| Broker redelivers a message | Inbox insert conflicts. The service re-emits its receipt. | No duplicate |
| Receipt lost | Relay republishes the row after 5 minutes. Service re-emits the receipt. | No loss |
| Service crashes mid-send | Lease expires. The row is re-sent with the same key. MailRelay drops it if it was already accepted. | No duplicate within the 24-hour key window |
| MailRelay down | Retries at 1, 2, 4 and 8 minutes. Then `failed` and page. | Failed and paged, not lost |
| Paging fails | Row is `failed` with `paged_at` null. A sweeper retries the page. | Not lost |
| Service database down | Consumer does not ack. The broker redelivers after 30 seconds. | No loss |
| Monolith database down | The caller's transaction fails, as it does today. | No row, so nothing to lose |

## Open questions

1. **Broker name, topology and retention.** Retention need not cover the worst outage, because the receipt loop republishes from the monolith. It should still be stated.
2. **MailRelay.** Is there a sandbox for staging? What happens if two sends with the same key are in flight at once? The lease must outlast the MailRelay timeout plus a margin. That avoids the race in practice but does not prove it safe. Can a dropped duplicate be told apart from a first send, for metrics?
3. **Render errors.** Today a render exception aborts the whole batch, and the row is retried on every poll, indefinitely. Proposal: a render failure counts as an attempt, so the row reaches `failed` and pages. This changes the retry policy and needs sign-off.
4. **Paging failures.** Who owns the `paged_at` sweeper?
5. **PII and secrets.** Email addresses and reset tokens will sit in the broker and the service database. Decide encryption at rest, broker access controls, and how long payloads are kept.
6. **Latency clocks.** Are the monolith and service clocks NTP-synced well enough for the p99 gate? If not, measure on one clock.
7. **Peak load.** The brief gives daily totals. Confirm peak per-second rates before step 5.
8. **Monolith status for service rows.** This plan mirrors status back to the monolith for support. Confirm that support tooling reads that mirror, not the service's table.