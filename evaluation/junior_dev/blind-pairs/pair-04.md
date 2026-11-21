# Pair 04

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

# Webhook delivery plan

This service sits between the `domain-events` topic (the queue) and customer endpoints. It turns each event into signed HTTP deliveries, retries failures, and dead-letters the ones that cannot succeed.

It has its own Postgres database, and all of its state is in one table, `deliveries`. One row is one (event, subscription) pair. Each row has a `status`: `pending`, `in_flight`, `delivered` or `dead`.

Retries do not use the queue. The queue's maximum delay is 15 minutes, and our waits go up to 6 hours. Instead, each row stores a `next_attempt_at` timestamp, and workers poll Postgres for rows that are due.

Components:
- **Dispatcher**: consumes `domain-events` and creates delivery rows.
- **Delivery workers**: several identical instances. They claim due rows and send them.
- **Admin API**: lists dead deliveries and replays them.
- **Cleanup job**: deletes old rows.

```mermaid
flowchart TD
    EV["domain-events message<br/>(may be a duplicate)"] --> DISP["Dispatcher: read active subscriptions<br/>for account_id whose event_types<br/>contain event_type or '*'"]
    DISP --> INS["One transaction: insert one row per subscription<br/>status=pending, attempt=0, next_attempt_at=now<br/>ON CONFLICT (event_id, subscription_id) DO NOTHING"]
    INS --> DB[("deliveries table<br/>service's own Postgres")]
    INS --> ACK["Commit, then ack the message"]

    DB --> CLAIM["Worker polls every ~1 s and claims one due row<br/>with FOR UPDATE SKIP LOCKED.<br/>Due = pending AND next_attempt_at <= now,<br/>or in_flight AND lease expired.<br/>Set in_flight, lease 30 s, attempt += 1"]
    CLAIM --> SUBCHK{"Subscription<br/>still active?"}
    SUBCHK -- "no" --> DEAD
    SUBCHK -- "yes" --> SEND["Decrypt secret, sign with t = now,<br/>POST with 10 s timeout"]
    SEND --> RES{"Result"}
    RES -- "2xx" --> DONE["status = delivered"]
    RES -- "408, 429, 5xx,<br/>timeout, connection error" --> TRY{"attempt < 8?"}
    TRY -- "yes" --> RETRY["status = pending<br/>next_attempt_at = now + wait<br/>after this attempt number"]
    RETRY --> DB
    TRY -- "no" --> DEAD["status = dead, set dead_at,<br/>record last status code or error"]
    RES -- "410" --> GONE["Disable subscription (reason 'gone');<br/>dead-letter this row and all of<br/>its pending rows"]
    GONE --> DEAD
    RES -- "other 4xx" --> DEAD

    DEAD --> ADMIN["Admin API: list dead rows per subscription;<br/>replay = status pending, attempt 0,<br/>dead_at cleared, same delivery id"]
    ADMIN --> DB
    CLEAN["Cleanup job: delete dead rows 14 days after dead_at<br/>and delivered rows 14 days after delivered_at"] --> DB
```

## Where state lives

`deliveries` is the only state this service owns. Columns:
- `id`: the delivery id, sent as `X-Webhook-Id`. It never changes, including on replay.
- `event_id`, `subscription_id`: unique together, so a duplicate event cannot create a second delivery.
- `body`: a copy of the event JSON, so sending never depends on another system. Events are at most 256 KB.
- `status`: `pending`, `in_flight`, `delivered` or `dead`.
- `attempt`: number of attempts started. A claim increments it before sending.
- `next_attempt_at`: when the row is next due.
- `lease_until`: when the current worker's claim expires.
- `last_status_code`, `last_error`: outcome of the latest attempt.
- `delivered_at`, `dead_at`: when the row reached that state. Used for retention.

Subscription data (url, secret, status) is read from the core database at send time, not copied, so edits apply immediately. The service writes only `status` and `disabled_reason` there.

## Behavior

**Matching and dedupe.** The dispatcher inserts all rows for a message in one transaction and acks the message after the commit. If it crashes before the ack, the queue redelivers the message, and the unique key makes the second insert a no-op.

**Multiple workers.** A worker claims a row with `FOR UPDATE SKIP LOCKED`, so no two workers take the same row. A new row is due immediately, so attempt 1 goes out about 1 s later (the polling interval).

**Crash recovery.** A claim sets a 30 s lease, which is longer than the 10 s timeout. If a worker dies mid-send, the lease expires and any worker claims the row again. That can send the same delivery twice. This is allowed: the guarantee is at-least-once, and the unchanged `X-Webhook-Id` lets receivers dedupe. No row is lost, because it stays in the table until it is delivered or dead.

Two rules keep this safe:
- A reclaim after a crash counts as an attempt. If the crashed attempt was already the 8th, the reclaim is dead-lettered instead of sent.
- A worker saves its result only if the row's `attempt` still equals the value it claimed. A slow worker whose lease expired therefore cannot overwrite a newer claim.

**Signing.** Each attempt is signed when sent: `X-Webhook-Signature: t=<now>,v1=hex(HMAC-SHA256(secret, "<t>.<raw body>"))`. A retry hours later still passes the receivers' 5-minute check.

**Retry waits.** After failed attempt 1 to 7, the wait before the next attempt is 30 s, 2 min, 10 min, 30 min, 1 h, 3 h and 6 h respectively. A failure of attempt 8 is dead-lettered.

**Disabled subscriptions.** A subscription can be disabled by a 410 or by the dashboard. Its waiting rows are dead-lettered, not sent and not silently dropped, with `last_error = 'subscription disabled'`. Workers check this at claim time. A 410 also dead-letters that subscription's pending rows immediately. Support can replay these rows after the customer re-enables the subscription. A replay is rejected while the subscription is still disabled.

**Replay.** The admin API lists a subscription's dead rows with `last_status_code` or `last_error`. A replay sets the row to `pending`, `attempt = 0`, `next_attempt_at = now`, and clears `dead_at`. The delivery id is kept, and the row gets a fresh cycle of 8 attempts.

**Retention.** Dead rows are deleted 14 days after `dead_at`. Delivered rows are also kept 14 days after `delivered_at`, so late duplicate events are still deduped. The 14 days for delivered rows is my choice, not a requirement. A duplicate event arriving after that could be delivered again.

---

# Document B

# Webhook delivery plan

Today the core app writes business events to an `outbox` table, and a relay publishes them to the `domain-events` queue topic. Customers register webhook endpoints in `webhook_subscriptions`, but nothing sends them events yet. This service reads each event from `domain-events`, writes one delivery row per matching subscription into its own Postgres database, and several worker instances send those rows as signed HTTPS POSTs. Workers retry on a fixed schedule and dead-letter what keeps failing. Retry state lives in Postgres, not in queue delays, because the queue delays a message by 15 minutes at most and our waits go up to 6 hours.

## Terms

- **Event**: one message on `domain-events`, JSON `{event_id, event_type, account_id, occurred_at, payload}`, at most 256 KB (the queue's limit, so a larger message never arrives). The same `event_id` can arrive more than once, because the queue and the relay are both at-least-once and unordered.
- **Subscription**: a row in the core database table `webhook_subscriptions`, written by the dashboard: `url` (https), `event_types` (exact names or `'*'`), `status` (`active` or `disabled`), `disabled_reason`, and an encrypted secret. This service may read it and may update only `status` and `disabled_reason`.
- **Delivery**: one row in our `deliveries` table for one (event, subscription) pair. Its `id` is the webhook id and never changes.
- **Dispatcher**: the part that consumes `domain-events` and creates deliveries.
- **Worker**: the part that sends deliveries. Every service instance runs the dispatcher, the worker and the cleanup job.
- **Lease**: a worker claims a delivery by pushing its `next_attempt_at` 60 s into the future. A row is claimable only when `status = 'pending'` and `next_attempt_at <= now()`, so a leased row is not due and no other worker takes it. If the worker dies, the row is due again after 60 s. A live worker finishes well inside the lease (see step 2).
- **Dead letter**: a delivery with `status = 'dead'` in the same table. It is not a queue.
- **Queue dead-letter topic**: the queue's own topic for messages that fail to be received N times. It cannot be queried or partly replayed, which is why our dead letters are table rows instead.

`deliveries` columns: `id`, `event_id`, `subscription_id`, `account_id`, `event_type`, `body` (the event JSON exactly as received), `status` (`pending`, `delivered` or `dead`), `attempt_count` (failed attempts so far), `next_attempt_at`, `last_status_code`, `last_error`, `dead_at`, `created_at`. `(event_id, subscription_id)` is unique. A partial index on `next_attempt_at` where `status = 'pending'` keeps the claim query cheap.

```mermaid
flowchart TD
    EV["domain-events message"] --> DISP["Dispatcher: find matching active subscriptions"]
    DISP --> INS["Insert delivery rows, skip existing pairs, then ack"]
    INS --> DB[("deliveries table, own Postgres")]
    DB --> CLAIM["Worker claims due row, lease 60 s"]
    CLAIM --> SUBCHK{"Subscription still active?"}
    SUBCHK -- "no" --> DEAD["Dead letter"]
    SUBCHK -- "yes" --> SEND["Sign and POST, 10 s timeout"]
    SEND --> RES{"Result"}
    RES -- "2xx" --> DONE["Delivered"]
    RES -- "408, 429, 5xx, timeout, connection error" --> MORE{"Attempts left?"}
    MORE -- "yes" --> WAIT["Set next_attempt_at by schedule"]
    WAIT --> DB
    MORE -- "no, 8th failure" --> DEAD
    RES -- "410" --> DIS["Disable subscription: gone"]
    DIS --> DEAD
    RES -- "other non-2xx" --> DEAD
    DEAD --> ADMIN["Admin API: list / replay"]
    ADMIN -- "replay: reset the same row" --> DB
    CLEAN["Cleanup job, hourly"] --> DB
```

## Steps

1. **Dispatch.** Trigger: the dispatcher pulls a `domain-events` message (several instances share the topic). It runs one query against the core database, with no caching and a 5 s timeout: active subscriptions with the event's `account_id` whose `event_types` contains the event type or `'*'`. In one transaction it inserts one `pending` delivery per match (new `id`, `attempt_count = 0`, `next_attempt_at = now()`) with `ON CONFLICT (event_id, subscription_id) DO NOTHING`, then acks the message. With no matches it just acks.
   - Duplicate message: the insert does nothing and the message is acked.
   - Crash after commit, before ack: the queue shows the message again after its visibility timeout, the insert does nothing, the ack follows. Nothing is lost or doubled.
   - Either database is down, the query times out or the transaction fails: no ack, and the queue redelivers.
   - A message that can never be processed (for example invalid JSON) is not acked and nothing else is done with it. After repeated failed receives it lands in the queue dead-letter topic.
2. **Claim.** Trigger: every worker polls about once a second and starts the next poll only after the previous batch has finished. A poll selects up to 20 due pending rows with `FOR UPDATE SKIP LOCKED`, so instances never take the same row, and sets their `next_attempt_at` to `now() + 60 s`. The 20 rows are sent in parallel, so a batch takes about 15 s at worst (5 s subscription read plus 10 s POST), inside the lease. Attempt 1 therefore goes out within about one poll interval of the event, a few seconds.
   - Worker crashes mid-send: the row is due again after 60 s and is sent again with the same `id` and the same attempt number, because `attempt_count` is written only after a result. The receiver may see a duplicate, which at-least-once allows.
3. **Check the subscription.** The worker reads the subscription by the delivery's `subscription_id` from the core database, with a 5 s timeout. It uses the current `status`, `url` and secret, so a changed URL or rotated secret applies to deliveries still waiting.
   - Subscription `disabled` or gone: dead-letter the delivery with `last_error = 'subscription disabled'` and send nothing. This is not an attempt: `attempt_count` and `last_status_code` stay as they were, and the admin list shows the row with that `last_error`. This is how deliveries already waiting for a disabled subscription are handled: each is dead-lettered when it next comes due, and stays replayable.
   - Core database unreadable in time: leave the row alone, `attempt_count` unchanged. The lease expiry makes it due again 60 s later. While the core database stays down this repeats every 60 s, with no limit set.
4. **Send.** The worker decrypts the secret with `libs/secrets.decrypt()`, then POSTs `body` (the whole event JSON) to the subscription URL with `Content-Type: application/json`, a 10 s timeout and no redirect following. Headers:
   - `X-Webhook-Id: <delivery id>`, the same on every attempt and every replay.
   - `X-Webhook-Signature: t=<unix seconds>,v1=<hex>`, where `v1` is HMAC-SHA256 over `<t>.<raw body>` keyed with the secret. The signed bytes are the stored `body` string exactly as sent, never re-serialized JSON. The signature is computed at send time on every attempt, so a resend has the same id but a new `t` and `v1`.

   A receiver recomputes the HMAC over `<t>.` plus the raw request bytes with its copy of the secret, compares it with `v1`, and rejects a `t` older than 5 minutes. It dedupes by remembering processed ids and ignoring repeats; a receiver that remembers ids for good will therefore ignore a replay too. The brief requires the same id on replays, so that is the receiver's choice.
   - Decrypt fails: treat it like an unreadable core database. Leave the row, count no attempt, and let the lease expire so it is tried again after 60 s.
5. **Record the result.** The write applies only if the row is still pending (`WHERE id = ... AND status = 'pending'`), so a stalled worker that finishes after its lease expired and another worker recorded a result changes nothing. At worst the receiver sees a duplicate.
   - 2xx: `delivered`.
   - 408, 429, any 5xx, a timeout or a connection error: add 1 to `attempt_count` and store `last_status_code` or `last_error`. If the new count is below 8, set `next_attempt_at = now() +` the wait for that count: 30 s, 2 min, 10 min, 30 min, 1 h, 3 h, 6 h for counts 1 to 7. At count 8, dead-letter. So the 6 h wait follows failure 7 only.
   - 410: dead-letter now and set the subscription's `status = 'disabled'`, `disabled_reason = 'gone'`. The dead-lettering does not depend on the disable write. If that write fails, the delivery is still dead-lettered, the subscription stays active, and the next event for it will most likely get a 410 and try again.
   - Any other non-2xx, including other 4xx and 3xx: dead-letter now, no retry.
   - Dead-lettering sets `status = 'dead'`, `dead_at = now()` and keeps the last status code or error.
   - The worker cannot write the result: the lease expires and the delivery is sent again with the same attempt number. The receiver sees the same id twice with different signatures (step 4).
6. **Support: list and replay (admin API).** Support staff call it. List takes a subscription id and returns that subscription's dead deliveries with `last_status_code` and `last_error`. Replay takes one delivery id (not a whole subscription) and resets that same row, keeping its `id`: `status = 'pending'`, `attempt_count = 0`, `next_attempt_at = now()`, `dead_at = null`. A fresh cycle of 8 attempts starts.
   - Errors: 404 if the delivery id does not exist. 409 Conflict with a short message if the row is not `dead`, or if its subscription is still disabled (it would be dead-lettered again at once).
7. **Cleanup.** Trigger: hourly on every instance (running twice is harmless). It deletes `dead` rows whose `dead_at` is older than 14 days, and `delivered` rows older than 14 days. Delivered rows are kept that long so a late duplicate event still hits the unique key.

## Rules that hold everywhere

- At-least-once, no ordering between events.
- Matching is decided when the event is dispatched. A subscription created or disabled later does not change deliveries already created, except through step 3.
- New events for a disabled subscription create no delivery. Re-enabling is done in the dashboard, outside this service, and affects only events dispatched afterwards. Support can replay the old dead ones.
- We add nothing to the core database.

## Open questions

- How many failed receives before the queue dead-letters a message that cannot be processed (the value of N)? Not decided.
- Who sets the queue's visibility timeout for the dispatcher? We assume the 30 s default is enough, since dispatch is one query and one transaction. Not confirmed.
- How is the admin API authenticated? Not covered by the brief.
- A delivery that keeps hitting an unreadable core database, a failing decrypt, or a worker crash is retried every 60 s with no limit. No cap is set yet, and whether decrypt can fail or hang is unknown.
- How does a customer get their webhook secret to verify signatures? The dashboard owns the secret; this service does not know how it is shown.
