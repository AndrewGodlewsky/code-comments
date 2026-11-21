## Outbound webhooks: delivery service

Customers already register webhook endpoints in the dashboard (rows in `webhook_subscriptions`, see `existing/schema.sql`). Every business event is already published by the outbox relay to the `domain-events` topic (see `existing/outbox-relay.md`, and read the queue facts at the end, because they limit your options). Build the service in between. It turns those events into signed HTTP deliveries, retries them, and dead-letters the ones that fail.

Fixed requirements:

- **Matching.** An event goes to every *active* subscription with the same `account_id` whose `event_types` contains the event type or `'*'`. Each (event, subscription) pair gets exactly one delivery. A duplicate `domain-events` message must not create a second one.
- **Request.** `POST` the event JSON to the subscription URL with a 10 s timeout. `X-Webhook-Id` carries the delivery id. It stays the same on every attempt and on replays, so receivers can dedupe. `X-Webhook-Signature: t=<unix seconds>,v1=<hex>`, where `v1` is HMAC-SHA256 over `<t>.<raw body>`, keyed with the subscription's secret. Receivers reject a `t` older than 5 minutes, so sign at send time, on every attempt.
- **Outcomes.** 2xx means delivered. 408, 429, any 5xx, a timeout or a connection error can be retried. On 410, dead-letter now and disable the subscription (`disabled_reason = 'gone'`). On any other 4xx, dead-letter now with no retry.
- **Retries.** At most 8 attempts. Attempt 1 should go out within a few seconds of the event. The waits before attempts 2 to 8 are 30 s, 2 min, 10 min, 30 min, 1 h, 3 h and 6 h. After the 8th failure, dead-letter.
- **Dead letters.** Support must be able to list a subscription's dead deliveries with the last status code or error, and replay one through an admin API. A replay keeps the delivery id and starts a fresh cycle of 8 attempts. Keep dead deliveries for 14 days.
- **Guarantees.** At-least-once. No ordering between events. A crashed worker must never lose a delivery. We will run several worker instances.
- **Storage.** The service gets its own Postgres database. Add nothing to the core database. You may read `webhook_subscriptions`, and you may update only its `status` and `disabled_reason`.

Up to you: how deliveries are stored and scheduled, how the instances share the work, how crashes are recovered, and what happens to deliveries already waiting when their subscription is disabled.

**Format:** a Mermaid flowchart of the whole path from a `domain-events` message to delivered or dead-lettered. Put short notes before or after it covering where state lives and what happens on failure.
