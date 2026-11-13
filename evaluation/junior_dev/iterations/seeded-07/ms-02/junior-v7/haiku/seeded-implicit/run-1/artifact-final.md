# Plan: extract notifications

Today, business code inserts a `pending` row into the monolith's `notifications` table inside its own transaction. A worker thread on every monolith instance sends each row through MailRelay and records the result in that same table. Sending competes with checkout for monolith CPU and database connections, so this plan moves sending one notification type at a time to a separate Notification Service with its own database. A per-type flag sets each row's route when the row is written, so exactly one side sends each row. The message broker carries each row to the service and carries the result back.

## Terms

- **MailRelay**: the outside email service that sends the mail. Its `send()` takes an optional `idempotency_key`. If MailRelay already accepted a send with that key in the last 24 hours, it drops the new send and reports success.
- **Notification id**: the uuid on each notification row. We pass it as the idempotency key on every send.
- **Broker**: the shared message queue that billing and search already use. It is at-least-once: a message not acknowledged within 30 seconds is delivered again, possibly to a different consumer. A publisher gets a confirmation once the broker has stored a message.
- **Ack**: a consumer's signal that it handled a message, so the broker stops redelivering it.
- **Flag**: a runtime setting read with `flags.get(name)`. A change reaches every monolith instance within 10 seconds.
- **Route**: a column on each row, `monolith` or `service`, set when the row is written. It names the side that sends the row.
- **Due**: a `pending` row whose `next_attempt_at` is now or earlier. A new row is due at once. After a failed send, the worker sets `next_attempt_at` to the retry time, and the row is due again then.
- **Outbox relay**: a thread in the monolith that publishes `service` rows to the broker. The `notifications` table is the outbox.
- **deliveries table**: the service's own table, with one row per notification id, that holds its send state.
- **SKIP LOCKED**: the `FOR UPDATE SKIP LOCKED` clause in a query. A row one worker has locked is skipped by the others, so two instances never take the same row at once.
- **Result message**: the message the service publishes on `notifications.result` after a row's final outcome, `sent` or `failed`.
- **Page on-call**: alert the engineer on call.
- **p99 latency**: the time within which 99% of sends finish.

The three types, all email only:

- `shipping_update`: a carrier webhook updates a shipment. About 40,000 a day.
- `order_confirmed`: checkout commits an order. About 12,000 a day.
- `password_reset`: a user asks to reset their password. About 1,500 a day.

## Rules every step must keep

- Callers do not change. Business code still calls `enqueue_notification(tx, ...)` inside its own transaction. The monolith's `notifications` table stays the first place each notification is recorded.
- Data stays separate. The service never reads or writes the monolith database, and the monolith never touches the service database. The broker is the only channel between them.
- Nothing is lost. Every notification whose transaction committed ends either accepted by MailRelay or marked `failed` with on-call paged.
- Nothing is duplicated, after a crash, a broker redelivery, a cutover or a rollback.
- Every send passes the notification id as `idempotency_key`. The old worker does this too, before any type moves.
- Retries are the same on both sides: 5 attempts, waiting 1, 2, 4 and 8 minutes before attempts 2 to 5, so 15 minutes in all. Any MailRelay error or timeout counts as one failed attempt. A timed-out send may already have been accepted, and the key covers that. After attempt 5 the row is marked `failed` and on-call is paged.
- Template rendering moves into the service.
- Rolling any type back to the monolith is a flag flip. It takes effect within a minute and neither loses nor re-sends notifications already in flight.

## How it runs

1. **Write the row.** Starts when checkout, the carrier webhook or the password-reset code calls `enqueue_notification(tx, ...)`. The function reads `notify.route.<type>` and inserts a `pending` row with that route into the monolith's `notifications` table. The row exists only if the caller's transaction commits. If the flag read fails, the row takes route `monolith`, the route the monolith already sends today. This keeps callers unchanged and means a flag outage does not fail checkout.

2. **The monolith worker sends its rows.** The existing worker runs on every monolith instance every 5 seconds. It takes up to 50 due `monolith` rows using SKIP LOCKED, and sends each one through MailRelay with its id as `idempotency_key`. It commits once per batch. A failed send follows the retry rule in the rules above, using the existing `attempts` and `next_attempt_at` columns on the same row. After attempt 5 the row is marked `failed` and on-call is paged, as it is today. If an instance crashes mid-batch, rows it sent but did not commit stay `pending` and are sent again with the same key. MailRelay drops the repeats within its 24-hour window. This ends the known problem, where a crash mid-batch re-sent about 30 emails a week, within that window.

3. **The outbox relay publishes service rows.** It runs as a thread on every monolith instance, every 5 seconds, like the worker. It takes up to 50 `service` rows where `published_at` is empty, using SKIP LOCKED. For each row it publishes a message to `notifications.requested` carrying the full row (id, type, email, payload), because the service cannot read the monolith database. It sets `published_at` on each confirmed row and commits once per batch. It does not use a created-at watermark, so a row committed late is still found. It does not check the flag: every unpublished `service` row is published, whatever the flag says now. The monolith row stays `pending`.

4. **The service stores the message.** The service's broker consumer reads `notifications.requested`. For each message it inserts a `deliveries` row with the message's id, type, email and payload, status `pending`, `attempts` 0 and `next_attempt_at` set to now. If a row with that id already exists, the insert does nothing. The consumer then acks. The monolith sees no change: its row stays `pending` with route `service`.

5. **The service sends.** A sender loop in each service instance polls every 5 seconds, the same as the monolith worker. It claims up to 50 due `deliveries` rows (status `pending`, `next_attempt_at` not later than now) using SKIP LOCKED. The first attempt is the first poll after the row is written, within about 5 seconds. The claim, the MailRelay call and the write-back run in one transaction, so the row stays locked for the whole send. Another instance skips a locked row, so two instances never send the same row at once. If the instance crashes, the lock is released and the row is sent again with the same key. The sender renders the template from the type and payload, then calls `mailrelay.send(to, subject, body, idempotency_key=id)`. On success it marks the row `sent`. On failure it adds 1 to `attempts`, applies the retry rule and stores the next attempt time in `deliveries`. After attempt 5 it marks the row `failed` and pages on-call itself, in the same transaction. The page does not go through the broker, so a broker outage does not stop it. If the page call fails, the marking rolls back and the row is tried again on the next poll. `deliveries` is the service's source of truth for send state. Sending and retries run from `deliveries`, not from the broker.

6. **The service reports the result.** After a final outcome, `sent` or `failed` after attempt 5, the service publishes a result message on `notifications.result` with the id and the outcome. After the broker confirms it, the service records `result_published_at` on the `deliveries` row. Each poll publishes any final row that has no `result_published_at`.

7. **The monolith records the result.** The monolith's result consumer finds its row by the message id and sets its status to match, `sent` or `failed`. It acks only after that update commits. It does not page, because the service has already paged on-call for a failed row. A repeated result sets the same status again, so it is harmless. Until the result arrives, the row stays `pending` with route `service`, and the monolith worker skips it.

## What happens when it goes wrong

| Step | Failure | What happens |
|---|---|---|
| 1 | The flag read in `enqueue_notification` fails | The row takes route `monolith` and the monolith worker sends it. The caller's transaction is not affected. |
| 2 | Monolith worker crashes after MailRelay accepts some of a batch, before the commit | Those rows stay `pending` and are sent again. MailRelay drops the repeat, so the user gets one email. |
| 3 | Relay crashes after publishing, before setting `published_at` | The message is published again. Step 4 skips it by id. |
| 3 | Broker does not confirm a publish | The relay stops the batch and commits the confirmed rows. The rest keep `published_at` empty and are retried on the next poll. Nothing is lost, because the caller already committed each row. |
| 4 | Service database is down, so the insert fails | No ack. The broker redelivers after 30 seconds. The monolith row stays `pending`. |
| 4 | Broker redelivers a message the service already has | The insert does nothing, and the consumer acks. No second send. |
| 4 | Two consumers receive the same message | The second insert does nothing, and that consumer acks. |
| 5 | MailRelay error or timeout | One failed attempt. `attempts` goes up by 1 and the retry rule applies. |
| 5 | Service crashes after MailRelay accepts, before recording | The row stays `pending`. On restart it is sent again with the same key. MailRelay drops it, so the user gets one email. |
| 5 | All 5 attempts fail | The row is marked `failed` and on-call is paged in the same transaction. If the page fails, the row is not marked `failed` and is tried again on the next poll. Then a failed result is published (step 6). |
| 6 | Broker does not confirm the result | Retried on every 5-second poll. |
| 6 | Service crashes after marking the row final, before publishing the result | The result is published again after restart. |
| 6 | Monolith status update fails | No ack. The broker redelivers after 30 seconds. |
| 6 | Result names an id with no monolith row | The consumer acks and raises an alert. Redelivery cannot fix a missing row. |
| 6 | Result never arrives | The row stays `pending` with route `service`. Alert on it (threshold open, see below). |
| Any | Flag flipped back to `monolith` | Monolith instances see the flag within 10 seconds, so new rows take the monolith path within the one-minute target. Rows already published finish on the service and report back. Unpublished `service` rows are still published by the relay, because it does not check the flag, so they also finish on the service. Nothing is re-sent, because the monolith never takes a `service` row. A row stuck unpublished because the broker is down waits there until the broker confirms, then sends on the service. The rollback does not move it to the monolith path. |

## Rollout, in order

Each step waits for the one before it. Before each type moves, check the type before it: it has run on the service for at least 3 days, and no alert on it is open for stuck `service` rows, the relay backlog or failed counts. The brief sets no other gate.

1. **Add idempotency keys to the existing worker.** Pass the notification id as `idempotency_key` on every send. No type has moved yet.
2. **Add the `route` and `published_at` columns and the per-type flags.** Add `route` and `published_at` to `notifications`. Set `monolith` as the column default and backfill every existing row with route `monolith`, because every existing row was written by the monolith's own enqueue. Ship the worker change (it takes only `monolith` rows) in the same deploy as the backfill, so no pending row is left without a route. Add `notify.route.<type>` for each type, all set to `monolith`. A flag change never changes a row already written.
3. **Build the Notification Service.** Give it its own database with a `deliveries` table, the consumer and sender described above, and copies of the templates. Deploy it separately.
4. **Add the outbox relay and the result consumer to the monolith.** Both run on every monolith instance. They do nothing until a type routes to `service`.
5. **Move `shipping_update`.** Set its flag to `service`. Leave it there for at least 3 days.
6. **Move `order_confirmed`.** Set its flag to `service` after step 5 has run for 3 days. Leave it there for at least 3 days.
7. **Move `password_reset`.** Do this only after the service has shown p99 enqueue-to-MailRelay latency under 60 seconds on `order_confirmed`.
8. **Remove the old worker.** Do this only after `password_reset` has run on the service for 7 days. Keep the old worker deployable until then. Before removing it, confirm that no `monolith` row is still `pending`. None should remain, since the retries total 15 minutes. Removal also ends rollback to the monolith for every type, because nothing sends `monolith` rows after that.

During each move, watch the relay backlog (unpublished `service` rows), failed counts and latency. Alert when a `service` row is still `pending` long after its publish, because that means the result has not arrived.

## Open questions

- MailRelay drops a repeated key only for 24 hours. What happens to a notification sent again after that window, for example after a long outage, is not known yet.
- Which screens, reports or other code read `notifications.status` is not known, so the effect of rows staying `pending` during service delivery is not known.
- The age at which a `service` row still `pending` should raise an alert is not set.
- The size of the unpublished `service` backlog that should raise an alert, during a long broker or service outage, is not set.
- The service sends each row once and reports one final outcome, so a `sent` and a `failed` result for the same id should not happen. What the consumer does if both arrive is not set.
- The MailRelay timeout is not in the files. It sets how long a row stays locked during a send in step 5.
- The levels of failed counts, latency and backlog that make a moved type healthy enough to move the next one are not set. The plan requires only that no alert is open.