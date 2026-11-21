# Plan: extract notifications into a Notification Service

## Summary

Today the monolith sends every notification itself. Business code writes a row to the `notifications` table inside its own transaction, and a worker in each monolith instance sends it through MailRelay. This plan moves sending into a separate Notification Service, one notification type at a time. Each row gets a `route` when it is written, so exactly one side ever sends it.

## Terms

- **Monolith**: the main app. It owns the `notifications` table and the old worker.
- **Route**: `monolith` or `service`. Set once, when the row is written, and never changed.
- **Relay**: a loop in the monolith that publishes `service` rows to the broker.
- **Broker**: a message queue with at-least-once delivery. A message not acknowledged within 30 s is sent again.
- **Service**: the Notification Service. It has its own database with a `deliveries` table, one row per notification id.
- **Idempotency key**: the notification id, sent with every MailRelay send. MailRelay drops a send whose key it accepted in the last 24 hours.

## How a notification flows

1. **Write.** Business code calls `enqueue_notification(tx, ...)` as it does today. The row's `route` comes from the flag `notify.route.<type>`. The row exists only if the transaction commits.
2. **Relay (service rows only).** The relay reads unpublished `service` rows, publishes each to `notifications.requested`, and marks it published after the broker confirms.
3. **Save.** The service consumer writes the notification id to `deliveries` as `pending`, then acknowledges the message. An id it already has changes nothing.
4. **Send.** The service's sender loop, like the old worker, takes due `pending` rows, renders the template, and calls MailRelay with the id as the idempotency key. On success it marks the row `sent`. On failure it waits 1, 2, 4, then 8 minutes between attempts, for 5 attempts in total. After the fifth failure it marks the row `failed` and pages on-call.

Monolith rows follow the same send steps in the old worker.

## What goes wrong

| What fails | What happens |
|---|---|
| Monolith crashes after commit, before sending | The row stays `pending` in the monolith table. The worker sends it. |
| Old worker crashes after MailRelay accepts, before committing | The row is sent again with the same key. MailRelay drops it. |
| Relay crashes after publishing, before marking published | The relay publishes again. The service ignores the repeat. |
| Relay crashes, or the broker is down | Rows stay unpublished and are sent late. Nothing is lost. Watch relay backlog. |
| Broker redelivers a message | The id is already in `deliveries`, so nothing new is saved. The message is acknowledged. |
| Service crashes before saving a message | The broker redelivers it after 30 s. |
| Service crashes after MailRelay accepts, before marking `sent` | The row is sent again with the same key. MailRelay drops it. |
| MailRelay is down or times out | The retry policy above applies. After 5 attempts the row is `failed` and on-call is paged. |
| Rollback (flag set back to `monolith`) | New rows route to the monolith within 10 s. Rows already on the service finish there, and the service keeps running until they do. No row changes side, so none is lost or sent twice. |

## Rollout steps, in ship order

Each step says what starts it, what changes, where its data lives, and what happens if it goes wrong.

1. **Add idempotency keys to the old worker.** Starts: deploy. Change: pass the notification id as `idempotency_key` on every send. Data: monolith table, unchanged. If it goes wrong: redeploy the previous version. The key covers repeats within MailRelay's 24-hour window, which includes all retries.
2. **Add the `route` column and the flags.** Starts: migration, then deploy. Change: add `route`, with existing rows set to `monolith`. The old worker picks only `route = 'monolith'`. Enqueue sets `route` from `notify.route.<type>`. A flag that cannot be read counts as `monolith`. Data: monolith table. If it goes wrong: the worker filter must ship with the column. Without it, the old worker would also send `service` rows.
3. **Build and deploy the service, idle.** Starts: deploy. Change: the service with its own database, `deliveries` table, broker consumer, sender loop, and copies of the templates. No type routes to it yet. Data: service database. If it goes wrong: nothing is sent, because no row reaches it. Until a type moves, template edits must go into both copies.
4. **Add the relay to the monolith.** Starts: deploy. Change: the relay publishes `service` rows to `notifications.requested`. Data: monolith table. If it goes wrong: see the relay rows above. No `service` rows exist yet, so this is idle too.
5. **Move `shipping_update`.** Starts: set `notify.route.shipping_update` to `service`. Change: new rows of this type route to the service. Data: monolith table until relayed, then service `deliveries`. Watch relay backlog, failed counts and latency. Keep it on the service for at least 3 days before step 6. If it goes wrong: flip the flag back (see rollback above).
6. **Move `order_confirmed`.** Same as step 5. Keep it on the service for at least 3 days before step 7.
7. **Move `password_reset`.** Starts: only after the service shows p99 enqueue-to-MailRelay latency under 60 s on `order_confirmed`. Measure from the row's `created_at` to the time MailRelay accepts it, recorded in `deliveries`. Then flip the flag. Watch and failure handling as in step 5.
8. **Remove the old worker.** Starts: `password_reset` has run on the service for 7 days. Keep the old worker deployable until then, because rollback needs it. Change: delete the worker and its code. Data: the monolith `notifications` table stays as the first record.

## Open questions

- Does MailRelay drop a send whose key matches a send still in progress, not yet accepted? The overview covers only accepted sends. If it does not, a duplicate is possible when a redelivery overlaps a slow send.
- How do `service` rows get their final status back to the monolith `notifications` table, if at all? The brief keeps that table as the first record, but the plan does not say how its status is updated.
- Who measures the latency gate, and where do failed counts for service rows appear?