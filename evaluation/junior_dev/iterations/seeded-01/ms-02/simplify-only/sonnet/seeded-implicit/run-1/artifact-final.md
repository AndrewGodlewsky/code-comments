# Plan: extract notifications into a Notification Service

Today the monolith's own worker sends notifications. Business code calls `enqueue_notification(tx, ...)`, which inserts a `pending` row into the monolith's `notifications` table inside the caller's transaction. A background thread on every instance then reads pending rows in batches, renders them, sends them through MailRelay, and commits once per batch. A crash between a MailRelay send and that commit causes duplicate emails (about 30 a week).

This plan moves sending into a separate Notification Service, one type at a time. The monolith still records every notification first. A relay in the monolith publishes each row to the message broker. The service consumes it, renders it, sends it, and records the result in its own database. A flag per type decides who sends, so rollback is a flag flip.

## Terms

- **Monolith**: the existing application. It owns the `notifications` table.
- **Service**: the new Notification Service. It owns its own database and its `deliveries` table. It never touches the monolith's database, and the monolith never touches its database.
- **Broker**: the message broker. It is the only link between the two sides. It is at-least-once: a message not acknowledged within 30 s is redelivered, possibly to another consumer.
- **MailRelay**: the email provider. If it has accepted a send with the same `idempotency_key` in the last 24 hours, it drops the new send and returns success.
- **Route**: a per-type flag `notify.route.<type>`, read through `flags.get`, with value `monolith` or `service`. A change reaches every monolith instance within 10 s.
- **Retry policy** (same everywhere): 5 attempts, waits of 1, 2, 4 and 8 minutes between them, then mark `failed` and page on-call.
- **Idempotency key**: the notification's id, passed on every MailRelay send.

## How it runs (once built)

1. **Record.**
   - Starts when: business code calls `enqueue_notification(tx, ...)` (unchanged).
   - Does: inserts the row as today, and also sets its `route` column from the current flag for its type.
   - State: the monolith's `notifications` table, committed with the caller's transaction.
   - If it fails: the caller's transaction rolls back and no notification exists.

2. **Publish.**
   - Starts when: the monolith's relay polls for rows with `route = service` that are not yet published.
   - Does: publishes each row (id, type, user email, payload) to `notifications.requested`, waits for the broker's confirmation, then marks the row `published`.
   - State: the `notifications` table.
   - If it fails: with the broker down or a crash before the mark, the row stays unpublished and is published again later. This can produce duplicate messages, which step 3 removes.

3. **Receive.**
   - Starts when: the service gets a message from the broker.
   - Does: inserts a `deliveries` row keyed on the notification id, then acknowledges. If the id already exists, it acknowledges and does nothing else.
   - State: the service's `deliveries` table.
   - If it fails: a crash before the acknowledgement causes redelivery, and the key makes that harmless.

4. **Send.**
   - Starts when: a service sender finds a `deliveries` row that is `pending` and due.
   - Does: renders the template, calls MailRelay with the notification id as `idempotency_key`, and marks the row `sent`.
   - State: the `deliveries` table, including attempt count and next attempt time.
   - If it fails: on a MailRelay error or timeout it applies the retry policy. After the fifth failure it marks the row `failed` and pages on-call. A crash after MailRelay accepted but before the mark leads to a resend, and MailRelay drops it because of the key (within 24 hours, which covers the 15 minutes of total backoff).

5. **Old path (monolith worker).**
   - Starts when: the existing worker polls, now only for rows with `route = monolith`.
   - Does: sends as today, plus the `idempotency_key`. Same retry policy.
   - State: the `notifications` table.
   - If it fails: same handling as today.

6. **Rollback.**
   - Starts when: someone flips a type's route back to `monolith`.
   - Does: new notifications of that type go to the old worker. Rows already published stay with the service and finish there. Rows not yet published are claimed by the old worker, because the relay only publishes rows marked `service`. The relay flips such a row's `route` back to `monolith` when it sees the flag has changed.
   - If it fails: a notification that both sides send is deduplicated by MailRelay through the shared key.

## What happens when things fail

| Failure | Result |
|---|---|
| Broker down | Rows stay unpublished in the monolith. The relay retries. Nothing is lost. |
| Message redelivered | The service sees the existing id and does nothing. |
| Service crashes mid-send | The row is still `pending`. It is retried, and MailRelay drops the duplicate. |
| MailRelay down | Retry policy. After 5 attempts the row is `failed` and on-call is paged. |
| Monolith crashes after publishing, before marking | The row is published again and the service ignores it. |

## Build and rollout order

1. Add `idempotency_key` to the old worker's MailRelay calls. Ship it.
2. Add the `route` column and the `notify.route.<type>` flags. All start as `monolith`.
3. Build the service: database, broker consumer, sender, templates.
4. Add the relay in the monolith.
5. Move `shipping_update` by setting its flag to `service`.
6. After 3 days, move `order_confirmed`.
7. After 3 more days, and only once p99 enqueue-to-MailRelay latency on `order_confirmed` is under 60 s, move `password_reset`.
8. After `password_reset` has run on the service for 7 days, remove the old worker.

During each move, watch the relay backlog, the failed count and latency.

## Open questions

- The mixed-state rollback step (step 6) relies on the relay flipping `route` back. The details of that claim are not settled.
- The service's table for in-flight state needs a decision on how long to keep `deliveries` rows.
