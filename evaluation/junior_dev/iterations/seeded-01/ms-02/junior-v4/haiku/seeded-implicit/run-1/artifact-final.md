# Plan: extract notifications into a Notification Service

## What this is and how it works today

Today, business code calls `enqueue_notification(tx, ...)` inside its own transaction. That writes a `pending` row to the monolith's `notifications` table, so the row exists only if the business change commits. A worker thread on every monolith instance polls that table every 5 seconds, sends each due row through MailRelay, and retries failures on a fixed schedule.

After this change, the call and the table stay. Sending moves, one notification type at a time, to a separate Notification Service with its own database. The message broker is the only link between the two.

## Terms

- **MailRelay**: our email provider. `send()` takes an `idempotency_key`. If MailRelay already accepted that key in the last 24 hours, it drops the new send and reports success.
- **Route**: a column on each `notifications` row that says who sends it, `monolith` or `service`. It is set once, when the row is created.
- **Flag**: `notify.route.<type>`, a runtime flag. When it is on, new rows of that type get route `service`. A change reaches every monolith instance within 10 seconds.
- **Outbox**: the `notifications` table. A `service` row with an empty `published_at` has not yet gone to the broker.
- **Broker**: the existing message broker. It delivers at least once. A message not acknowledged within 30 seconds is delivered again.
- **Deliveries**: the service's own table, one row per notification id. It holds the live attempt count.
- **Retry schedule**: 5 attempts in total. After attempt 1 fails, wait 1 minute. After attempt 2, wait 2 minutes. After attempt 3, wait 4 minutes. After attempt 4, wait 8 minutes. If attempt 5 fails, mark the row `failed` and page on-call. A timeout or a template render error counts as a failed attempt. The sender sets `next_attempt_at` to now plus the wait, using the new attempt count.

## Main flow

There are five steps. Each one says what starts it, what it does, where its data lives, and what happens when it fails. The failure table below lists every failure in one place.

1. **Enqueue**
   - Starts: business code, inside its own transaction.
   - Does: inserts the row as it does today. If the type's flag is on, the row gets route `service`. Otherwise it gets `monolith`.
   - Data: `notifications`.
   - If it fails: if the flag read fails, the row gets `monolith`, and the transaction still commits.

2. **Publish**
   - Starts: a relay thread in every monolith instance, every 5 seconds.
   - Does: reads `service` rows with an empty `published_at`, oldest first. For each row, it publishes (id, type, email, payload, created_at) to `notifications.requested`, waits for the broker's confirmation, then sets `published_at`.
   - Data: `notifications`. The relay takes no lock. Two instances can publish the same row, and step 3 ignores the second copy.
   - If it fails: the row stays unpublished, and the next loop tries again.

3. **Store**
   - Starts: a message on `notifications.requested`.
   - Does: inserts a `deliveries` row with the same fields, status `pending`, `attempts` 0 and `next_attempt_at` now, so the next poll sends it. If a row with that id already exists, it does nothing. The consumer acknowledges the message only after the insert commits.
   - Data: the service's `deliveries`.
   - If it fails: no acknowledgement is sent, so the broker redelivers the message within 30 seconds. The insert then does nothing.

4. **Send**
   - Starts: the sender's poll, every 5 seconds.
   - Does: takes up to 50 `pending` rows whose `next_attempt_at` has passed, using `FOR UPDATE SKIP LOCKED`, so senders never share a row. The whole batch is one transaction. For each row, the sender renders the template and calls MailRelay with the notification id as `idempotency_key`. Then:
     - **Accepted:** publish a `sent` result (id, attempts) to `notifications.result`, wait for confirmation, then set the row to `sent`.
     - **Rejected or timed out, attempt 1 to 4:** add 1 to `attempts` and set `next_attempt_at` from the retry schedule. Publish nothing.
     - **Rejected or timed out, attempt 5:** page on-call, publish a `failed` result (id, attempts), wait for confirmation, then set the row to `failed`.
     - **Template render fails:** treat it as a rejected attempt for this row only. The other rows carry on.
     - **Result publish not confirmed:** leave the row `pending` with `attempts` unchanged. The next poll sends it again with the same key.
     - **Any other error, such as a database error:** roll back the whole batch.
   - The result is published before the row changes, so a crash cannot lose a result.
   - Data: `deliveries`. Locks are held until the batch commits. A slow MailRelay call makes the batch longer, and other senders skip its rows.
   - If it fails: see the failure table.

5. **Copy back**
   - Starts: a result on `notifications.result`.
   - Does: a consumer in the monolith sets `status` and `attempts` on the `notifications` row with that id. It updates only while the row is `pending` with route `service`. It acknowledges the message after the update commits. A repeated result finds a row that is no longer pending, so it changes nothing. A result for a missing row or a `monolith` row should not happen. The consumer logs it and acknowledges it.
   - Data: `notifications`.
   - If it fails: no acknowledgement is sent, so the broker redelivers within 30 seconds. The row stays `pending`.

For a `service` row, the monolith row stays `pending` with `attempts` at 0 until the final result arrives. The live attempt count is in `deliveries`.

## What happens when things fail

| What fails | What happens |
|---|---|
| Relay crashes after publishing, before setting `published_at`, or two instances publish the same row | The row is published again. Step 3 ignores the extra copy. |
| Broker is down during publish | The row stays unpublished. The next 5-second loop tries again. |
| Service consumer crashes before acknowledging | The broker redelivers within 30 seconds. The insert does nothing. |
| Sender crashes during a MailRelay call | The row is still `pending`. The next poll sends it again with the same key. |
| Sender crashes after MailRelay rejects, before the attempt update | The old `attempts` and `next_attempt_at` stay, so the next poll sends again. One attempt is not counted. A rejected send is safe to repeat. |
| Sender crashes after MailRelay accepts, before the result is published | The row is still `pending`. The next poll sends again. MailRelay drops the repeat and reports success, and the result is published. |
| Result publish fails (broker down) | The row stays `pending` and attempts are not counted. The sender retries every 5 seconds, with the same key and no limit, until the broker confirms. See open questions. |
| Sender crashes after paging, before the row changes | The next poll makes the attempt again. If it fails, on-call is paged again. A repeated page is not a repeated email. |
| MailRelay is down or times out | A failed attempt. The retry schedule applies. |
| Template render fails | A failed attempt for that row only. The other rows in the batch carry on. |
| Other error in the batch, such as a database error | The batch rolls back. Rows already sent in it return to `pending` and are sent again with the same key. MailRelay drops the repeats. Published `sent` results are harmless. Published `failed` results are not, because the row can later be sent. See open questions. |
| Result consumer fails, or the monolith is down | No acknowledgement, so the broker redelivers within 30 seconds. The row stays `pending`. The old worker ignores it, because its route is `service`. |
| Result arrives twice | The second copy changes nothing. |
| Service is down | Unpublished rows wait in the outbox. Published messages wait on the broker. Stored messages wait in `deliveries`. Nothing is lost or sent twice. |

## Rollout (shipping order)

Each step ships on its own. Steps 5 to 7 move one notification type each.

1. **Idempotency keys on the old worker.** Starts: deploy. Each send passes the row id as `idempotency_key`. Data: `notifications`, unchanged. If it fails: a resend after a crash is dropped by MailRelay. This also removes the duplicate emails caused by the per-batch commit.
2. **Route and `published_at` columns, and the flags.** Starts: migration. Existing rows get `monolith`. `published_at` is empty. `enqueue_notification` sets the route from the flag, defaulting to `monolith`. The old worker picks up only `monolith` rows. With all flags off, nothing changes.
3. **Build the Notification Service.** Starts: deploy, with its own database and its own copy of the three templates. It receives nothing yet. Data: the service's database only.
4. **Add the relay and the result consumer to the monolith.** Starts: a thread in every instance, every 5 seconds. Nothing is routed to the service yet.
5. **Move `shipping_update`.** Starts: turn on `notify.route.shipping_update`. Steps 3 and 4 must already be live. Run for at least 3 days. Watch relay backlog, failed counts and latency.
6. **Move `order_confirmed`.** Starts: 3 days after step 5, with no open problems. Run for at least 3 days.
7. **Move `password_reset`.** Starts: 3 days after step 6, and only when the service shows p99 enqueue-to-MailRelay latency under 60 seconds on `order_confirmed`. Over the 3-day run, the service measures, for each `order_confirmed` row, the time from the message's `created_at` to MailRelay's acceptance. The service never reads the monolith's database.
8. **Remove the old worker.** Starts: 7 days after `password_reset` moves to the service. Delete the worker thread and its `monolith` query. No data moves. Until this step, the old worker stays deployable.

## Rollback

Rollback works one type at a time, by flipping a flag.

1. Turn `notify.route.<type>` off. Every monolith instance sees the change within 10 seconds.
2. New rows of that type get route `monolith`. Rows already created keep their route.
3. The relay still publishes unpublished `service` rows, and the service still finishes them. The old worker touches only `monolith` rows.
4. Each row has one route, so only one side sends it. Nothing is sent twice or dropped.

Do not stop the service until its `pending` rows in `deliveries` reach zero.

## Open questions

- MailRelay's key blocks repeats for only 24 hours. Can the broker deliver a message more than 24 hours after its first delivery? If it can, a duplicate is possible. The same risk applies if the broker stays down for more than 24 hours during a result publish, because the sender keeps retrying with the same key.
- A `failed` result can be published, and then the batch can roll back. The row returns to `pending` and may later be accepted by MailRelay. The monolith keeps the first result, so the row can show `failed` while the email was sent. Should the `failed` result wait until the batch commits?
- How long can a flag read take? If it can block, checkout waits with it.
- Do the monolith and service host clocks agree closely enough for a 60-second latency check?