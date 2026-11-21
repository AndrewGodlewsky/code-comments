# Plan: extract notifications into a Notification Service

## Summary

Today every monolith instance runs a worker thread that sends notifications. Business code calls `enqueue_notification(tx, ...)` inside its own database transaction. That inserts a `pending` row into the monolith's `notifications` table, and the row exists only if the transaction commits. The worker reads due rows, renders each email, sends it through MailRelay and records the result. The worker runs inside the monolith, so it competes with checkout for CPU and database connections. It also commits once per batch, so a crash mid-batch can send the same email again. Support sees about 30 duplicate emails a week.

This plan moves sending into a separately deployed Notification Service with its own database. Business code does not change. The monolith's `notifications` table is still the first place each notification is recorded. When a row is created, a flag sets its route: the old worker or the service sends it. Each row has exactly one sender, so a flag flip cannot send a row twice. The monolith publishes service rows to a message broker. The service stores each message, renders the email and sends it. The MailRelay idempotency key and the service's deliveries table stop repeats.

Types move one at a time, in this order: `shipping_update`, then `order_confirmed`, then `password_reset`. Moving a type to the service, or back, is a flag flip. All three types are email only. About 40,000 `shipping_update`, 12,000 `order_confirmed` and 1,500 `password_reset` notifications are created per day.

The plan keeps these rules:
- Every notification whose enqueuing transaction committed ends in one of two states: accepted by MailRelay, or `failed` with on-call paged.
- No user gets the same notification twice. This holds after a crash, after broker redelivery, during cutover and during rollback.
- Every send passes the notification id as MailRelay's `idempotency_key`. The old worker does this too, before any type moves.
- Retries follow today's policy on whichever side sends: 5 attempts, waits of 1, 2, 4 and 8 minutes, then `failed` and an on-call page.
- The monolith and the service never read or write each other's database. The broker is the only channel between them, and it is at-least-once.

## Terms

- **Monolith**: the main application. It runs business code and holds the `notifications` table.
- **Notification**: one email to one user, created by a business event.
- **MailRelay**: the outside email provider. Its `send()` takes an optional `idempotency_key`. If MailRelay already accepted a send with that key in the last 24 hours, it drops the new send and reports success.
- **Idempotency key**: the notification's id, sent to MailRelay with every send.
- **Enqueue**: a call to `enqueue_notification(tx, ...)`. It inserts a `pending` row into the monolith's `notifications` table. The row exists only if the caller's transaction commits.
- **Route**: a column on each `notifications` row. `monolith` means the old worker sends it. `service` means the Notification Service sends it. It is set at enqueue and never changes. The default is `monolith`.
- **Flag**: a runtime setting read with `flags.get(name)`. A change reaches every monolith instance within 10 seconds. The flag `notify.route.<type>` sets the route of new rows of that type.
- **Old worker**: the thread in every monolith instance that sends `pending` rows with route `monolith`.
- **Outbox relay** (the relay): a loop in every monolith instance. It publishes `service` rows to the broker, then records that it did.
- **Broker**: the message broker that billing and search already use. It is at-least-once. A message not acknowledged within 30 seconds is redelivered, possibly to another consumer. A publisher gets a confirmation once the broker has stored the message.
- **Acknowledge**: telling the broker a message is handled, so it is not redelivered.
- **Published**: a monolith row whose `published_at` is set. The relay sets it after the broker confirms the message.
- **Notification Service** (the service): the separately deployed service. It has its own database, a consumer, a sender and the email templates.
- **Consumer**: the part of the service that receives broker messages and stores them in the deliveries table.
- **Sender**: the part of the service that sends emails through MailRelay.
- **Deliveries table**: the service's own table, with one row per notification, keyed by notification id. It holds the id, type, recipient email, payload, creation time, status, attempt count, next attempt time and `accepted_at`, the time MailRelay accepted the send.
- **Template**: the email layout for one type. It turns a payload into a subject and a body. The sender picks the template by the row's type.
- **Due**: a `pending` row whose next attempt time has passed.
- **Attempt**: one try to send a notification. There are 5 in total.
- **Claim**: a short committed transaction that adds 1 to the attempt count and sets the guard time. The sender makes a claim before each MailRelay call.
- **Guard time**: the next attempt time that a claim sets while a send runs. It keeps other instances from taking the row until the send has ended. A failure write replaces it.
- **Backoff**: the wait before each retry. The waits are 1, 2, 4 and 8 minutes, before attempts 2 to 5.
- **Row lock (`FOR UPDATE SKIP LOCKED`)**: a read that skips rows another worker has locked, so two workers never take the same row.
- **Enqueue-to-MailRelay latency**: the time from a row's creation to MailRelay accepting its send. A p99 under 60 seconds means 99% of notifications beat 60 seconds.
- **Backlog**: the number of `service` rows that are not yet published. The relay counts it in the monolith, because the service cannot read that database.
- **Failed count**: the number of service rows marked `failed` in the deliveries table.
- **On-call page**: an alert sent to the on-call engineer.

## How it runs

These steps follow one `shipping_update` notification with route `service`. Today the old worker does the same work inside the monolith. Step 6 covers the old path.

1. **Create.** A carrier webhook updates a shipment and calls `enqueue_notification` inside its own transaction. The flag `notify.route.shipping_update` is on, so the row gets route `service`. When the transaction commits, the monolith's `notifications` table holds the row: id, type, user id, email, payload, creation time, route `service`, status `pending` and an empty `published_at`. If the transaction rolls back, no row exists and nothing is sent.
   - Data kept: monolith `notifications`.

2. **Publish.** The relay starts on a 5-second poll in every monolith instance. It opens a transaction and reads up to 50 rows with route `service` and no `published_at`, locked with `FOR UPDATE SKIP LOCKED`, so two instances never take the same row. For each row it publishes to the topic `notifications.requested`. The message carries the id, type, email, payload and creation time. When the broker confirms a message, the relay sets `published_at` on that row. The lock is held from the read until the batch commits, so it covers every publish and confirmation. The relay commits once per batch. Checkout only inserts rows, so it never waits on these locks.
   - If the broker does not confirm a row, its `published_at` stays empty and the next poll tries again.
   - If the broker is down, rows wait in the monolith. Sends are delayed, not lost.
   - If the relay crashes after the broker stored a message but before the commit, the row is published again. Step 3 ignores the copy.
   - Data kept: monolith `notifications`.

3. **Store.** The consumer starts when it receives a message. It inserts a deliveries row with the id, type, email, payload and creation time, status `pending`, zero attempts and a next attempt time of now. The message holds everything the sender needs, so the service never reads the monolith's database. If the id already exists, the insert does nothing. The consumer acknowledges the message after the insert commits, whether the row is new or already existed. The consumer never sends email. Only step 4 sends.
   - If the consumer crashes before it acknowledges, the broker redelivers the message within 30 seconds, possibly to another consumer. The insert is then a no-op, and the message is acknowledged.
   - If the row is already `sent` or `failed`, nothing is inserted or sent, and the message is acknowledged.
   - Data kept: service deliveries.

4. **Claim and send.** The sender starts on a 5-second poll in every service instance. Each poll takes up to 50 due rows, the same values the old worker uses today.
   - **Read.** The sender reads up to 50 due ids in one read. That read holds no lock after it returns. No lock is held while the sender claims or sends.
   - **Claim, one row at a time.** Each row gets its own short committed transaction. It locks the row with `FOR UPDATE SKIP LOCKED`, then checks that the row is still `pending` and due. If the lock is taken or the row is no longer due, the sender skips it. Otherwise:
     - If the row already has 5 attempts, the sender sets status `failed`, pages on-call with the id, and does not send. This happens only after a crash during attempt 5.
     - Otherwise it adds 1 to the attempt count and sets the guard time to now plus the backoff before the next attempt. That is 1 minute after attempt 1, 2 minutes after attempt 2, 4 after attempt 3 and 8 after attempt 4. After attempt 5 the guard is 1 minute.
     - The sender counts the attempt before the send, so a crash during a send still uses up an attempt. The guard keeps other instances off the row while the send runs.
   - **Render and send.** After the claim commits, the sender picks the template for the row's type and renders it from the row's payload. It then calls MailRelay `send` to the row's recipient email, with `idempotency_key` set to the notification id. The call times out after 45 seconds. That is less than the 1-minute guard, so a send ends before its row is due again.
   - **Sent.** If MailRelay accepts the send, the sender sets status `sent` and `accepted_at` to the time it received MailRelay's success.
   - **Failed.** A render error, a MailRelay error or a timeout goes to step 5.
   - The `sent` and `failed` writes apply only while the attempt count still equals the count this sender claimed. A late write from a sender that lost its claim changes nothing.
   - Data kept: service deliveries.

5. **Retry and fail.** This step runs when an attempt fails: a render error, a MailRelay error or a timeout. The sender sets the next attempt time to the failure time plus the backoff for that attempt, as today's worker does. So a failed attempt 1 is retried 1 minute after it fails, not 1 minute after the claim. Retries come from the deliveries table, not from broker redelivery, because step 3 already acknowledged the message. After attempt 5 fails, the sender sets status `failed`, pages on-call with the notification id and the error, and sets no next attempt time.
   - If this write fails or arrives after the guard time, the row is due at its guard time. The next claim sends it again with the same key.
   - Data kept: service deliveries.

6. **Old path (route `monolith`).** The old worker selects due `pending` rows with route `monolith`. It renders the template and sends with the notification id as `idempotency_key`. It uses the same policy: 5 attempts, backoff of 1, 2, 4 and 8 minutes, then `failed` and an on-call page. A render error counts as a failed attempt. Today a render error escapes the batch uncounted, so this changes. The old worker's state is the monolith's `notifications` row, and it still commits once per batch. A crash mid-batch can send rows again, but they keep the same key, so MailRelay drops the repeats.
   - Data kept: monolith `notifications`.

7. **Where the status lives.** A `service` row's status (`sent` or `failed`) is written only to the deliveries table. The monolith row stops at `published_at`. Its status stays `pending` for good, and nothing reads it. The old worker and the relay select rows by route, not by status. Nothing changes or removes a monolith row after it is published. A failed service notification is visible only in the deliveries table and in the on-call page.

8. **Rollback.** Setting `notify.route.<type>` back to `monolith` changes the route of new rows only. The change reaches every monolith instance within 10 seconds, so new rows go to the old worker within a minute. A row keeps the route it was given. Rows routed to `monolith` are sent by the old worker. Rows routed to `service` that are not yet published are still published by the relay, and rows already in the service are still sent by it. The relay and the service keep running until those rows drain. Each row has one sender, so nothing is re-sent and nothing is dropped.

## What happens when things fail

| What fails | What happens | Where the data is kept |
|---|---|---|
| Monolith crashes after commit, before publish | The row has no `published_at`. The relay publishes it after restart. | Monolith `notifications` |
| Monolith crashes after the broker stored a message, before confirmation or commit | The relay publishes the row again. The service's insert does nothing for the copy. | Service deliveries primary key |
| Broker is down | The relay cannot publish. Rows wait in the monolith. Sends are delayed, not lost. | Monolith `notifications` |
| Service consumer crashes before acknowledging | The broker redelivers within 30 seconds, possibly to another consumer. The insert is a no-op if the row exists, and the message is acknowledged. | Service deliveries |
| Redelivered message for a row already `sent` or `failed` | Nothing is inserted or sent. The message is acknowledged. | Service deliveries |
| Service crashes before the claim commits | Nothing is counted. The row is still due and is picked up on the next poll. | Service deliveries |
| Service crashes after the claim, during or after a send | The attempt is counted. The row is due at its guard time and is sent again with the same key. MailRelay drops the repeat if it accepted the first send, for 24 hours after that send. | Service deliveries, MailRelay key |
| Service crashes during attempt 5 | The row is due 1 minute after the claim. The sender marks it `failed` and pages on-call without sending. If MailRelay had accepted the email, on-call gets a page for a sent email. No duplicate is sent. | Service deliveries |
| MailRelay accepts the send, but the `sent` write fails | The row stays `pending` and is due at its guard time: 1, 2, 4 or 8 minutes after attempts 1 to 4. The repeat send with the same key is dropped, and the sender then writes `sent`. Exception: after attempt 5 the row is due after 1 minute, marked `failed` and paged, although the email was sent. | Service deliveries, MailRelay key |
| A send runs past 45 seconds | The MailRelay call times out before the guard time. It counts as a failed attempt, and the retry uses the same key. | Service deliveries |
| The failure write fails, or arrives after the guard time | The row is due at its guard time. The next claim sends it again with the same key. | Service deliveries, MailRelay key |
| Template rendering fails | Counts as a failed attempt. The retry policy applies. After attempt 5, the row is `failed` and on-call is paged. | Service deliveries |
| MailRelay is down or times out | Counts as a failed attempt. The retry policy applies. After attempt 5, the row is `failed` and on-call is paged. | Service deliveries |
| Old worker crashes mid-batch after some sends | The rows are sent again with the same key, and MailRelay drops the repeats. This should stop the known duplicate emails. It is not yet measured. | Monolith `notifications`, MailRelay key |
| Service is down during a rollback | Rows routed to `service` wait in the broker or in the monolith. How long the broker holds them is open. See Rollback. | Monolith `notifications`, broker |

## How we roll it out

Each deploy is separate. Do not start a deploy until the one before it has passed its gate. A gate is the check named at the end of each deploy.

- **Deploy 1: idempotency keys on the old worker.** The old worker sends the notification id as `idempotency_key` on every send. It also counts a render error as a failed attempt under the same policy. No type has moved. Gate: the new code runs on every monolith instance.
- **Deploy 2: route column, publish column and flags.** Add `route` with default `monolith`, and add `published_at`. Existing rows get route `monolith`. Add the flags `notify.route.<type>`, all off. The old worker's query now takes only route `monolith` rows. Add `created_at` to the broker message for latency measurement. Gate: the new code runs on every monolith instance. No flag may be turned on before this gate passes. An instance on older code does not filter by route, so after a flip it could send service rows that the relay also publishes. That would break the one-sender rule, and MailRelay's key would drop the second send only within 24 hours.
- **Deploy 3: build the Notification Service.** It has its own database with the deliveries table, a broker consumer, a sender and the templates, which move out of the monolith. No traffic reaches it yet. Gate: the service runs with its consumer and sender active, and no traffic reaches it.
- **Deploy 4: outbox relay in the monolith.** It publishes route `service` rows to `notifications.requested`. Until a flag is on, it has nothing to publish. Gate: the relay runs on every monolith instance, and the backlog is zero.
- **Deploy 5: move `shipping_update`.** Turn on `notify.route.shipping_update`. It must run on the service for at least 3 days before deploy 6. Watch the backlog, the failed count and the enqueue-to-MailRelay latency. Gate for deploy 6: at least 3 days on the service.
- **Deploy 6: move `order_confirmed`.** Turn on `notify.route.order_confirmed` only after `shipping_update` has run on the service for at least 3 days. It must run on the service for at least 3 days before deploy 7. Watch the same three measures. Gate for deploy 7: at least 3 days on the service.
- **Deploy 7: move `password_reset`.** Turn on `notify.route.password_reset` only after the service has shown p99 enqueue-to-MailRelay latency under 60 seconds on `order_confirmed`. Watch the same three measures.
- **Deploy 8: remove the old worker.** Only after `password_reset` has run on the service for 7 days. Until then, keep the old worker deployable, so a rollback to the monolith stays possible. After removal, a flag flip no longer sends monolith rows, so a rollback would need a redeploy of the old worker. The brief's flag-flip rule does not cover that. See open questions.

## Open questions

- Which window is the p99 latency measured over, and do retries count toward it?
- Which clock records enqueue time and MailRelay accept time, given that they run on different hosts?
- Does the monolith need the final `sent` or `failed` status for service rows? The service cannot write it back today. A status message on the broker would need a separate plan.
- How long does the broker keep an unacknowledged message if the service is down during a rollback?
- Do the relay and the flags stay after deploy 8?
- Who looks up the final status of a service notification, for example to answer a support question, when the monolith row shows only `published_at`?
- Who checks each gate, and what counts as a bad backlog, failed count or latency? The brief names the measures but gives no thresholds.
- Do deploys 1 to 4 need checks beyond "running on every instance"?
- After deploy 8, a flag flip cannot send monolith rows. Should the old worker stay deployable beyond deploy 8, or is a redeploy an accepted rollback?
- The MailRelay key protects for 24 hours. Is that enough if the sender is down for about a day?
- The 45-second MailRelay timeout and the 1-minute guard are chosen in this plan, not set by the brief. Are they right for MailRelay's real latency?