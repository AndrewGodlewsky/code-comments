# Plan: Extract notifications into a Notification Service

## Core design

Read this before the steps. Every step relies on these rules.

- **The monolith table is still the first record.** `enqueue_notification` is unchanged and still inserts inside the caller's transaction. The `notifications` table doubles as the outbox.
- **Each row has exactly one owner.** A new nullable column `owner` takes the values `NULL` (unclaimed), `'monolith'`, or `'service'`. Whichever component claims a row sets `owner` in the same transaction that takes the row lock. No row can be sent by both sides, even if instances disagree on a flag for the 10 s propagation window.
- **Ownership is sticky.** Once a row is owned, its owner finishes it, whatever the flag says later. A flag flip only decides who claims unclaimed rows.
- **Intent before publish.** The relay commits `owner = 'service'` before it publishes to the broker. A row that might have reached the broker can therefore never be sent by the monolith. This closes the publish, crash, flag-flip case.
- **The service dedupes by notification id.** Its own table is keyed by `id`. The consumer inserts and acks only after commit. Sends pass `idempotency_key = id`.
- **Status flows back by broker only.** The service publishes `sent` and `failed` events. A monolith consumer applies them to its own rows. Neither side touches the other's database.
- **Routing flags.** `notifications.route.<type>` is `monolith` or `service`, defaulting to `monolith`. If the flag read fails, use `monolith`, since the monolith can always send.

## Steps

### 1. Key and per-row commit on the existing worker

- **Starts when:** the monolith build with this change is deployed. Nothing else changes.
- **Data moves:** nothing new. Each `send()` passes `idempotency_key = row.id`.
- **State lives:** the monolith `notifications` table, unchanged.
- **Change:** commit after each row instead of after each batch. A crash then re-sends at most the one row whose acceptance was not committed.
- **On failure:**
  - Crash after MailRelay accepts but before commit: the row stays `pending` and is re-sent with the same key. MailRelay drops it within 24 h.
  - MailRelay timeout: handled as today. The key makes the retry safe.
  - Rollback: redeploy the previous build. Old sends with a key are harmless.

### 2. Ownership columns and claim rules in the monolith worker

- **Starts when:** an additive migration (`owner`, `published_at`, `first_attempt_at`, all NULL by default), then deploy, then creation of the three `notifications.route.*` flags set to `monolith`.
- **Data moves:** nothing.
- **State lives:** monolith table and flags.
- **Change:** the worker claims rows where `status = 'pending' AND next_attempt_at <= now() AND (owner = 'monolith' OR (owner IS NULL AND type routes to monolith))`. Each claim sets `owner = 'monolith'` and `first_attempt_at` in the same per-row transaction that sends.
- **On failure:**
  - Mixed versions during deploy are safe. Old instances process `NULL` rows without writing `owner`, and the new code still claims them. The relay is not running yet.
  - A crash mid-send rolls back the transaction, so the row returns to `NULL` and is re-sent with its key.
  - Rollback of the migration is not needed, since it is additive.

### 3. Monolith relay (dark until a type routes to service)

- **Starts when:** a relay loop runs on every monolith instance every 5 s. Row locks make several instances safe.
- **Data moves:**
  - For rows with `owner IS NULL` and a service-routed type, in batches of up to 50: commit `owner = 'service'` (`FOR UPDATE SKIP LOCKED`). This is the intent commit.
  - Publish `{id, type, email, payload, created_at, schema_version}` to the notification topic.
  - On broker confirmation, set `published_at`.
  - Retry publish for rows where `owner = 'service' AND published_at IS NULL`. This ignores the flag.
- **State lives:** `owner` and `published_at` in the monolith table are the durable record. The broker holds the messages.
- **On failure:**
  - Crash after intent, before publish: the restarted relay publishes the row. It is never sent by the monolith.
  - Crash after publish, before `published_at`: republished. The service dedupes.
  - Broker down: rows stay `owner = 'service'` and unpublished. Nothing is sent by the monolith. Alert on the age of the oldest unpublished row.
  - The relay keeps running after any rollback until no unpublished `owner = 'service'` rows remain.

### 4. Status consumer in the monolith (dark)

- **Starts when:** the monolith subscribes to the status topic.
- **Data moves:** events `{id, status: sent|failed, accepted_at, attempts}` are applied as `UPDATE notifications SET status = ... WHERE id = ? AND owner = 'service' AND status = 'pending'`.
- **State lives:** monolith table.
- **On failure:** duplicate or redelivered events are no-ops. Terminal states are set once. Until an event arrives, the monolith row shows `pending`, which is the correct support view.

### 5. Build the Notification Service (no live traffic)

- **Starts when:** the service is deployed to its own runtime with its own database. No flag routes to it yet.
- **Data moves:**
  - *Ingest:* the consumer inserts into `notifications` (`id` primary key, `type`, `email`, `payload`, `status` in `queued | sending | sent | failed`, `attempts`, `next_attempt_at`, `lease_until`, `first_attempt_at`, `accepted_at`, `created_at`) with `ON CONFLICT (id) DO NOTHING`, then acks the broker. Ack only after commit.
  - *Render:* templates are copied into the service. Golden tests must show byte-identical subject and body against the monolith for all three types.
  - *Send:* claim rows where `status = 'queued' AND next_attempt_at <= now()`, or with an expired lease, via `FOR UPDATE SKIP LOCKED`. Set `status = 'sending'`, increment `attempts`, set `first_attempt_at` if unset, and set a lease. Call MailRelay with `idempotency_key = id`.
  - *Outcome:* on success, mark `sent` and set `accepted_at`. On failure, if `attempts >= 5`, mark `failed` and write a page intent. Otherwise queue again with `next_attempt_at = now() + [1, 2, 4, 8][attempts-1]` minutes.
  - *Events:* status events are written to a service outbox table in the same transaction as the state change, then published by a relay. This avoids losing an event after a commit.
- **State lives:** service database only. Page intents are published by a pager job.
- **On failure:**
  - Service crash during send: the lease expires, the row is re-claimed, and the send uses the same key. MailRelay drops it if already accepted.
  - Broker down: the consumer is idle. Queued rows still send.
  - MailRelay down: backoff runs. After 5 attempts, the row is `failed` and on-call is paged. Retries span about 15 min, as today.
  - Guard: if `first_attempt_at` is more than 20 h old and the row is not terminal, mark it `failed` and page. Never re-send, because the key window is 24 h.
  - Pages can duplicate. That is acceptable, since paging is not user-facing.

### 6. Staging rehearsal and fault injection (gate for step 7)

- **Starts when:** step 5 is in staging.
- **Data:** synthetic traffic at production rates (40,000, 12,000, and 1,500 per day).
- **Tests:**
  - `kill -9` the monolith and the service at each boundary: after claim, after publish, after ingest commit, after accept.
  - Force broker redelivery.
  - MailRelay fake returning 5xx, timeouts, and accept-then-lost-reply.
  - Measure end-to-end flag flip time, including the 5 s poll and 10 s propagation.
  - Roll back mid-flight with rows owned by both sides.
  - Simulate a 30 min broker outage.
- **Gate:** zero duplicate accepts per id on the MailRelay fake. Every committed row reaches a terminal state, confirmed by reconciliation.
- **On failure:** any failing test blocks step 7.

### 7. Move `shipping_update`

- **Starts when:** step 6 gates pass. Set `notifications.route.shipping_update = service` in production.
- **Data moves:** new `shipping_update` rows are claimed by the relay and sent by the service. Rows already owned by the monolith finish there.
- **State lives:** monolith `owner` and `status`, service table, broker.
- **Hold:** at least 3 days. Done when all of these hold:
  - no duplicate reports from support;
  - every service-owned row reaches a terminal state (reconciliation query);
  - failure and paging rates are within the monolith baseline;
  - the oldest unpublished row is under the alert threshold.
- **Rollback:** set the flag back to `monolith`. The change takes effect within a minute. Service-owned rows drain on the service. The relay keeps running. The service may not be scaled to zero until `owner = 'service' AND status IN ('queued','sending')` is empty.

### 8. Move `order_confirmed`

- **Starts when:** step 7 has held for 3 days and passed. Same mechanics and rollback as step 7.
- **Latency measurement starts here.** Define enqueue-to-MailRelay as `accepted_at - created_at`. Clock sync between database and service hosts must be tight enough that skew is well below 60 s.

### 9. Hold `order_confirmed` and evaluate the latency gate

- **Starts when:** step 8 is live.
- **Hold:** 3 days.
- **Gate:** p99 enqueue-to-MailRelay under 60 s on `order_confirmed` (service-owned rows only).
- **On failure:** do not start step 10. Investigate and rerun the hold.

### 10. Move `password_reset`

- **Starts when:** steps 8 and 9 have passed.
- **Data moves:** `password_reset` rows follow the same path.
- **Rollback:** the same flag flip as before. This is the most latency-sensitive type, so run the rollback drill in staging before prod.

### 11. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days, and this query returns zero: rows with `status = 'pending' AND owner IN (NULL, 'monolith')`.
- **Actions:**
  - Remove the monolith worker loop and its claim code.
  - Keep the old worker artifact deployable until day 7. Do not delete it earlier.
  - Remove the `notifications.route.*` flags.
  - Keep the relay and status consumer. They are the only path to the service.
- **On failure:** if pending monolith-owned rows remain, do not remove the worker. Investigate first.
- **After this step**, rollback to the monolith is no longer possible.

## Decisions needed

1. **Crash counts as an attempt.** The service increments `attempts` at claim, so a crash mid-send uses up an attempt. Today's worker rolls back and does not count it. Counting it bounds poison messages, but it can fail a notification sooner than today. Confirm.
2. **p99 gate scope.** Does the 60 s gate include retried sends? Any send that needs a retry takes at least 1 min, so if more than 1% of sends retry, p99 fails regardless of pipeline speed. Confirm whether to gate on all accepted rows or first-attempt rows only, and report both.
3. **Personal data on the broker.** Email and payload travel on the broker, which billing and search also use. The service cannot read the monolith database to look them up. Confirm the data policy allows this, or encrypt the email field.
4. **20 h guard.** Rows with a first attempt older than 20 h and no terminal state are failed and paged, never re-sent. Confirm this trade-off.

## Residual risks

- The MailRelay key window is 24 h. A duplicate is possible only if a row's outcome is unknown after 24 h. Step 5's guard turns that case into a page, not a duplicate.
- Restoring either database from a backup can roll state back and cause re-sends. Restore procedures must check `owner` and `status` before the service or monolith resumes sending.
- Status events and page intents depend on their outboxes. Alert on the age of the oldest unpublished item in each.