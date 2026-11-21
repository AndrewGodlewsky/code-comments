# Notification Service extraction plan

## Summary

Today, a worker thread inside the monolith sends notifications. Business code writes a `pending` row to the `notifications` table inside its own transaction. The worker checks for pending rows every 5 seconds, sends them through MailRelay (our email provider) in batches of up to 50, and commits once per batch. Sending competes with checkout for CPU and database connections. If an instance dies mid-batch, some emails are sent again: support sees about 30 duplicates a week.

This plan moves sending into a separate Notification Service with its own database. Business code does not change, and the monolith's `notifications` table stays the first record of every notification. The monolith publishes each committed row to a message broker. The service stores the message, renders the email, sends it, and reports the result back through the broker. Each notification type moves to the service one at a time, using a flag. The old worker stays deployed until the last type has run on the service for 7 days, so any type can move back.

Duplicates are prevented by one rule. Every MailRelay send carries the notification's id as its idempotency key. MailRelay accepts a send with a given key once within 24 hours and drops any repeat. Volume is small, about 53,500 notifications a day, so the constraints that matter are no loss, no duplicates, the latency gate and safe rollback. Throughput is not the constraint.

## Terms

- **Notification row:** a row in the monolith's `notifications` table. It is written inside the business transaction, so it exists only if that transaction commits.
- **Outbox:** the rows the monolith still has to publish. The publisher reads only committed rows, so a message exists exactly when its row was committed.
- **Broker:** the message system that billing and search already use. It delivers at least once. A message not acknowledged within 30 seconds may be sent again, possibly to another consumer.
- **Ack:** the consumer's signal to the broker that it has handled a message.
- **Inbox:** the service's table of received messages, keyed by notification id. A repeated message is ignored.
- **Claim:** a worker marks a row as its own by changing its status, in a short transaction, before doing slow work.
- **Lease:** a time limit on a claim, stored in `lease_until`. If the worker dies, the row can be claimed again after the lease expires.
- **Idempotency key:** a value sent with each email. MailRelay drops a repeat send with the same key within 24 hours.
- **Flag:** a runtime setting, `notif_route.<type>`, set to `monolith` or `service`. A change reaches every monolith instance within 10 seconds.
- **Attempt:** one try to send a row through MailRelay. A row gets at most 5.
- **Handed off:** the monolith has published the row and the broker has confirmed it is stored. From then on, the service owns the row.

## How a notification moves

Each type is routed by its flag. A type on `monolith` is sent by the monolith worker. A type on `service` is published by the monolith and sent by the service. The monolith's row changes state as shown below.

| Status | Meaning | Held by | Next states |
|---|---|---|---|
| `pending` | Committed, not claimed | nobody | `sending` (monolith route) or `publishing` (service route) |
| `sending` | Monolith sender holds a lease | monolith | `sent`, `failed`, or `pending` (retry) |
| `publishing` | Publisher holds a lease | monolith | `handed_off`, or `pending` (broker error) |
| `handed_off` | Broker confirmed; service owns the row | service | `sent` or `failed`, from a status event |
| `sent` | Done | nobody | none |
| `failed` | Done; on-call paged | nobody | none |

These rules hold in every step:

1. Enqueueing does not change. `enqueue_notification(tx, ...)` still inserts a `pending` row inside the caller's transaction. If the business transaction rolls back, no row exists and nothing is published.
2. Only a claim gives a worker ownership of a row. A flag decides which claimer runs for a type. Two workers never hold the same row at once, except after a lease expires.
3. Every MailRelay send carries `idempotency_key = notification id`. This covers crashes, redelivery, two versions running during a rollout, and a row passing from one sender to the other.
4. The service acks a broker message only after its inbox row is committed. The inbox insert is `INSERT ... ON CONFLICT (id) DO NOTHING`, so a repeat is harmless. A repeat also re-sends the row's current status event.
5. The service never checks the flag. It accepts every message it receives, so messages already in flight are not stranded when a type rolls back.
6. Every handoff, reclaim and retry finishes well inside MailRelay's 24-hour window. Leases last minutes, and the whole retry schedule takes 15 minutes. The open questions cover the rest.

The retry policy is the same on both senders. A row gets up to 5 attempts. The sender waits 1, 2, 4 and 8 minutes before attempts 2 to 5. If attempt 5 fails, the sender marks the row `failed` and pages on-call.

## Steps

The steps are in the order we ship them. Steps 1 to 5 build the system with no traffic moved. Steps 6 to 8 move one type at a time. Step 9 removes the old code.

### Step 1. Expand the monolith schema

- **Starts:** the migration ships before any code that uses it.
- **Data moves:** none. No backfill.
- **State:** the monolith database. Add two nullable columns, `lease_until` and `handed_off_at`. If `status` has a CHECK constraint or enum, widen it to allow `sending`, `publishing` and `handed_off`.
- **If it fails:** the change is additive and nullable, so the current worker ignores it. If a rollback is needed, leave the columns in place.

### Step 2. Old worker: idempotency key and per-row claim

- **Starts:** deploy of the changed `run_worker`. No type moves yet.
- **Data moves:** each MailRelay send passes `idempotency_key = row.id`.
- **What it does:** in a short transaction, the worker claims up to 50 pending rows. It sets `status = 'sending'`, adds 1 to `attempts`, and sets `lease_until` to 5 minutes from now. It calls MailRelay outside any transaction, then commits each row's result on its own. This replaces the one commit per batch. A row whose `sending` lease has expired is reclaimed, and each reclaim counts as an attempt. The retry policy does not change.
- **State:** the monolith database.
- **If it fails:**
  - The worker crashes after MailRelay accepted the send: the lease expires, and the retry sends the same key. MailRelay drops it.
  - The worker crashes before the call: there is no duplicate, because MailRelay never accepted the first call.
  - MailRelay times out: the timeout is an error, and the row is retried with the same key.
  - Old and new instances both run during the rollout: both may send the same row. The key makes that safe.
- **Gate:** staging shows MailRelay drops a second send with the same key, and support-reported duplicates fall.

### Step 3. Publisher and status consumer, routing still off

- **Starts:** deploy. Every `notif_route.<type>` flag is `monolith`.
- **Data moves:** none. The publisher claims only `pending` rows whose type is routed to the service. With all flags on `monolith`, it does nothing.
- **Broker:** create the topic `notifications`, keyed by notification id, and the consumer group `notif-service`. Retention is an open question.
- **Messages:**
  - Enqueue message: the row's id, type, user id, email, payload and enqueue time.
  - Status event: the id, the new status, when it was accepted or failed, and the last error.
- **Publisher:** claims service-routed `pending` rows as `publishing`, with a 5-minute lease. It publishes each row, waits for broker confirmation, then sets `handed_off` and `handed_off_at`. On a broker error, it sets the row back to `pending` with a short delay.
- **Status consumer:** moves a `handed_off` row to `sent` or `failed`. It ignores rows in any other state, so it never moves a row backwards.
- **If it fails:** if the publisher or broker is down, rows wait in `pending`. Nothing is lost and nothing is sent. Alert on the age of the oldest pending row.

### Step 4. Deploy the service with no traffic

- **Starts:** the service's deploy. The service database is created with no grants to the monolith database, and the service holds no monolith credentials.
- **Contents:**
  - the broker consumer;
  - the service's own `notifications` table, with the same columns as the monolith's plus `status`, `attempts`, `next_attempt_at`, `lease_until`, `accepted_at` and `last_error`;
  - a `status_outbox` table, which holds status events waiting to go back to the monolith;
  - the sender worker;
  - templates copied from the monolith;
  - a MailRelay client that always sends the idempotency key;
  - metrics and alerts.
- **Data moves:** none yet.
- **If it fails:** no traffic is flowing, so nothing is at risk. Dashboards and alerts must work before step 5.

### Step 5. Staging and fault-injection gate

- **Starts:** step 4, in staging, against the MailRelay sandbox.
- **Tests:**
  - Kill the sender after the MailRelay call and before the commit. Expect one accepted send per id.
  - Deliver the same broker message three times. Expect one inbox row and a repeated status event.
  - Make MailRelay fail for 20 minutes. Expect retries at 1, 2, 4 and 8 minutes, then `failed` and one page.
  - Take the service down for 1 hour under load. Expect no loss after recovery.
  - Flip flags in both directions under load. Expect no id sent twice and none lost.
  - Roll back a business transaction. Expect no row and no message.
- **Pass:** every id reaches `sent` or `failed` exactly once, every failure produces one page, and the sandbox report shows no id accepted twice.

### Step 6. Cut over `shipping_update`

- **Starts:** set `notif_route.shipping_update = service`. Within 10 seconds, the publisher starts handing off this type's rows.
- **Data flow, one notification:**
  1. The publisher hands off the pending row to the broker, keyed by id.
  2. The service writes the message to its inbox, commits, and acks.
  3. The sender claims the row as `sending`, with a lease.
  4. The sender renders the templates and sends through MailRelay with the key.
  5. The result is written to the service's `notifications` table. A `status_outbox` row is written in the same transaction.
  6. The status event goes back over the broker.
  7. The monolith sets the row to `sent` or `failed`.
- **State:** the monolith's `notifications` table is the outbox and the record. The service's `notifications` and `status_outbox` tables hold the working state.
- **If it fails:** see the failure table below. Only the service pages for a row it sends.
- **Soak:** at least 3 days. Exit when the daily checks are clean, the failure rate is at or below the rate before the cutover, and the p99 age of the backlog is under 60 seconds.

### Step 7. Cut over `order_confirmed`

- **Starts:** step 6 has exited. Set `notif_route.order_confirmed = service`.
- **Mechanics:** as in step 6.
- **Latency:** for each row, enqueue-to-accept is the service's `accepted_at` minus the monolith's `enqueued_at`. Record the p99 for each day and across the whole soak.
- **Soak:** at least 3 days. Exit when the p99 is under 60 seconds across the whole soak and no single day exceeds 60 seconds. This is the gate for step 8.
- **If it fails:** as in step 6. A broker outage longer than about 60 seconds breaks this latency target. The open questions cover how to handle that.

### Step 8. Cut over `password_reset`

- **Starts:** step 7's latency gate has passed. Set `notif_route.password_reset = service`.
- **Mechanics:** as in step 6, with the latency alarm applied to this type.
- **Soak:** at least 7 days.
- **Old worker:** stays deployed and idle for the whole soak. It is the rollback sender for all three types.
- **If it fails:** roll back, as described in the Rollback section.

### Step 9. Remove the old worker

- **Starts:** 7 days after step 8 completes, with no rollback open.
- **Removes:** `run_worker`, the monolith sender branch, the `notif_route` flags, and the monolith's copies of the templates.
- **Keeps:** `enqueue_notification`, the publisher and the status consumer. The monolith's `notifications` table stays the record.
- **If it fails:** a rollback after this point needs a sender to be added back. The open questions cover this.

## Rollback (any type, at any time)

1. Set `notif_route.<type> = monolith`. Within 10 seconds, the publisher stops claiming that type, and the monolith sender starts claiming its `pending` rows.
2. Rows already `handed_off` stay with the service, which keeps consuming and sending them. Do not stop the service's consumer or sender until its inbox for the type is empty.
3. Expired `publishing` leases for the type are reclaimed by the monolith sender. The broker may already have confirmed some of these rows, so the same id can reach both senders. The key blocks a second accepted send within the 24-hour window. The 5-minute lease keeps the overlap to minutes.
4. Normally nothing is sent twice. The monolith never resends a `handed_off` row, and the service never sends a row it has already marked `sent`.
5. Confirm that the `pending` count for the type reaches zero, the service's inbox for the type drains, and the daily checks are clean.

## Daily checks (run during every cutover)

- **No loss:** every committed row older than about 1 hour is `sent` or `failed`. Any other row pages on-call.
- **Stalled handoffs:** a `handed_off` row with no status after 1 hour is republished. The inbox ignores the repeat, and the service re-emits the status.
- **No duplicates:** compare the service's log of accepted sends with the monolith's record. Any id accepted more than once pages on-call.
- **One page per failure:** each `failed` row has exactly one page, raised by the sender that marked it failed.

## What happens when things fail

| Failure | What happens | Why nothing is lost or sent twice |
|---|---|---|
| Old worker crashes after MailRelay accepted the send | The lease expires, and the retry sends the same key | MailRelay drops the repeat |
| Publisher crashes after broker confirmation, before `handed_off` | The lease expires, and the message is published again | The inbox ignores the repeat |
| Broker is down | Rows wait in monolith `pending`. Alert on their age | Nothing is handed off, so nothing is sent |
| Broker redelivers an unacked message | The inbox ignores the repeat, and the status event is re-emitted | The inbox is keyed by id |
| Service is down | Unacked messages are redelivered after 30 seconds. On return, the inbox ignores repeats | The service acks only after its inbox commit |
| MailRelay is down or times out | Retries at 1, 2, 4 and 8 minutes, then `failed` and one page | The key covers each retry |
| Render error | Counted as a failed attempt, so it cannot loop | The attempt counter |
| Flag flipped while rows are in flight | The flag only affects claiming. Messages already in flight are still accepted | The service never checks the flag |
| Business transaction rolls back | No row and no message | The row is the outbox |

## Open questions

1. **Broker retention.** The overview does not give it. Retention must cover the longest outage we will tolerate. I suggest at least 72 hours. Billing and search share the broker, so their owners must confirm.
2. **MailRelay's 24-hour window.** A duplicate is not guaranteed if an attempt is re-sent more than about 20 hours after its first send. Retries and reclaims finish within an hour. A service that is down for a day can hold an attempt that MailRelay accepted but that was never recorded. Proposal: the sender stops resending any row whose unrecorded attempt is older than 20 hours, and pages on-call for manual reconciliation. The cost is that a notification that was actually sent may be marked `failed`, but it will not be sent twice.
3. **Personal data on the broker.** Email addresses and payloads cross the broker and are stored in the service database. Confirm topic access controls, encryption at rest and retention. The service cannot read the monolith database, so it cannot look up the email instead.
4. **MailRelay sandbox.** Confirm that the sandbox honours the idempotency key, and whether MailRelay can report accepted sends by key. Without that, step 5 and the duplicate check cannot produce proof.
5. **Latency clocks.** Enqueue time comes from the monolith database clock. Accept time comes from the service clock. The plan assumes clock skew under 1 second. The latency dashboard must state that assumption.
6. **Template ownership.** Templates exist in both places from step 4. Either freeze edits to the three types until step 9, or ship each edit to both copies in the same release.
7. **Keep a sender after removal?** The brief removes the old worker 7 days after `password_reset` moves. Rolling back after that means adding a sender back. The alternative is to keep the sender code behind the flag indefinitely.
8. **Automatic fallback.** The plan has no automatic switch back to the monolith when the broker or service is unhealthy. Flags are changed by hand. An automatic fallback would be safe in principle, because the key covers overlap. But it would hide breaches of the 60-second `password_reset` target, including breaches caused by a broker outage.