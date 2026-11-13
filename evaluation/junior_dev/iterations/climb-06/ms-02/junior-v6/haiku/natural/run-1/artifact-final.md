# Plan: Extract notifications into a Notification Service

## Summary

Today, business code calls `enqueue_notification(tx, ...)` inside its own database transaction. That inserts a `pending` row into the monolith's `notifications` table. A worker thread on every monolith instance then sends pending rows through MailRelay, our email service. The worker runs in the same processes that serve checkout, so the two compete for CPU and database connections. The worker commits once per batch. If an instance dies partway through a batch, some rows are sent again. Support sees about 30 duplicate emails a week.

This plan moves sending into a separate Notification Service with its own database and its own deployment. The move happens one notification type at a time, behind a routing flag, in this order: `shipping_update`, `order_confirmed`, `password_reset`. Business code does not change. The monolith's `notifications` table stays the first record of every notification.

For a type that has moved, a monolith relay publishes each new row to the message broker. The service stores the row, sends it through MailRelay, and publishes the result. The monolith applies that result to its own row.

Why this shape: the monolith keeps the record and the enqueue path, so callers do not change. Each row has exactly one sender, recorded in its `owner` column. The monolith sets the owner before it publishes, so a row that might have reached the service is never sent by the monolith. A row that already has an owner finishes with that owner. A row nobody has claimed yet follows the flag at the moment it is claimed, because nobody has sent it. This is what makes rollback a flag flip.

The rules every step must keep:

- **Nothing lost.** Every committed notification ends up either accepted by MailRelay, or marked failed with on-call paged.
- **Nothing duplicated.** A user never gets the same notification twice. This holds after a crash, a broker redelivery, a cutover, or a rollback. Every send passes the notification's `id` as the idempotency key.
- **Same retry policy on either side.** 5 attempts. Waits of 1, 2, 4 and 8 minutes before attempts 2 to 5. Then mark the row failed and page on-call.
- **Separate data.** The service has its own database. Neither side reads or writes the other's database. The broker is the only channel between them, and it is at-least-once.

## Terms

- **MailRelay**: the external email service we send through. Its `send()` takes an optional `idempotency_key`. If MailRelay has already accepted a send with that key in the last 24 hours, it drops the new send and returns success. A dropped repeat looks the same to the caller as a new accept. We pass no key today.
- **Idempotency key**: the value we pass to MailRelay with each send. It is the notification's `id`. The old worker passes it too, before any type moves.
- **Broker**: the message broker that billing and search also use. It is at-least-once. A message not acknowledged within 30 seconds is redelivered, possibly to a different consumer. A publisher gets a confirmation once the broker has stored the message.
- **Notification topic**: the broker topic that carries rows from the monolith to the service.
- **Status topic**: the broker topic that carries results from the service back to the monolith.
- **Owner**: a column on the monolith's `notifications` table. `NULL` means nobody has claimed the row. `monolith` means the monolith sends it. `service` means the service sends it.
- **Claim**: taking a row to send it. The claimer locks the row with `FOR UPDATE SKIP LOCKED` and sets `owner` in the same transaction, so two workers cannot take the same row.
- **Routing flag**: `notifications.route.<type>`, set to `monolith` or `service`. The default is `monolith`. The monolith reads it with `flags.get(name)`. The service never reads flags. A change reaches every monolith instance within 10 seconds.
- **Relay**: a monolith loop that publishes rows of service-routed types to the notification topic. It runs every 5 seconds on every monolith instance.
- **Status consumer**: a monolith loop that applies status events from the status topic to monolith rows.
- **Outbox**: a table in the service database. An event is written in the same transaction as the change it reports. A separate loop publishes it later, so a committed change never loses its event.
- **Attempt**: one try at sending. The service counts an attempt when it claims a row, before it calls MailRelay.
- **Lease**: a time limit (`lease_until`) that the service sets on a row while it sends. When the lease expires, the row can be claimed again.
- **Terminal state**: `sent` or `failed`. Once a row reaches one, it does not change.
- **Page intent**: a row in the service database that says on-call must be paged about one failed notification.
- **Pager job**: a scheduled service job that turns unsent page intents into pages.
- **Reconciliation**: a query that joins the monolith and service `notifications` tables on `id`. It checks that every committed row has a terminal state on the side that owns it, and that no `id` has more than one accepted send at MailRelay. Who runs it is an open question.

## How a notification is sent

For a type routed to the monolith, steps 1 and 2 apply. For a type routed to the service, steps 1 and 3 to 8 apply. A row with owner `NULL` is not sent by either side until it is claimed. The flag read at the moment of the claim decides which side claims it.

### Step 1: Enqueue

- **Starts when:** business code calls `enqueue_notification(tx, ...)` inside its own transaction (checkout, carrier webhook, password reset).
- **What it does:** inserts a row with status `pending`, owner `NULL`, and 0 attempts. The row exists only if the caller's transaction commits. If the caller rolls back, no row exists and nothing is sent.
- **Where the data lives:** the monolith `notifications` table.
- **If it goes wrong:** nothing was recorded, so nothing is sent. The caller's transaction decides.

### Step 2: Monolith claim (monolith-routed types)

- **Starts when:** each monolith instance runs this loop every 5 seconds.
- **What it does:** selects up to 50 rows where status is `pending`, `next_attempt_at <= now()`, and either owner is `monolith`, or owner is `NULL` and the type routes to the monolith. Each row is handled in its own transaction:
  - set owner to `monolith`, and set `first_attempt_at` if it is unset;
  - render the subject and body with the monolith's templates;
  - call MailRelay with `idempotency_key = id`;
  - record the result.

  Each row commits on its own, so a crash repeats at most the one row whose result was not committed. The row keeps owner `monolith` between attempts.
- Rows of a service-routed type with owner `NULL` are skipped. They stay `NULL` until the relay claims them.
- **Where the data lives:** `owner`, `first_attempt_at`, `attempts`, `status` and `next_attempt_at` in the monolith table. They are set in the same transaction as the send.
- **If it goes wrong:**
  - MailRelay error or timeout: the failure path below.
  - Crash mid-send: the transaction rolls back. Owner returns to `NULL`, and `attempts` and `first_attempt_at` do not move. The next claim decides who sends the row, by the flag it reads then. The same key is used either way, so MailRelay drops a send it already accepted within 24 hours.
  - Failure path: add 1 to `attempts`. At attempt 5, set status `failed` and page on-call in the same transaction, as today. Otherwise set `next_attempt_at` to now plus the wait: 1 minute after attempt 1, 2 minutes after attempt 2, 4 minutes after attempt 3, 8 minutes after attempt 4.
  - An error that is not a MailRelay error: see the open questions.
- **Paging:** the monolith pages its own failed rows at attempt 5, as today.

### Step 3: Relay, intent then publish (service-routed types)

- **Starts when:** each monolith instance runs this loop every 5 seconds. Several instances can run it safely, because row locks stop double claims.
- **What it does**, in three parts:
  - a. **Intent.** Claims up to 50 rows with owner `NULL` whose type routes to the service. It sets owner `service` with `FOR UPDATE SKIP LOCKED` and commits. This commit happens before any publish. Nobody has sent these rows, so either side could take them. The flag read at claim time decides which side does.
  - b. **Publish.** Sends `{id, type, email, payload, created_at, schema_version, attempts, first_attempt_at}` to the notification topic. `attempts` is the row's current count. If `attempts` is above 0 but `first_attempt_at` is `NULL` (rows the old worker sent during rollout step 2), the relay sends `created_at` in its place. That starts the 20-hour clock early, which is safe.
  - c. **Confirm.** When the broker confirms, the relay sets `published_at` in a separate short update.
- **Retry:** rows with owner `service`, `published_at` `NULL`, and status `pending` are published again, whatever the flag says. If the confirmation has not come back when the retry runs, the broker can get two copies. The service dedupes them. This costs one extra broker message.
- **Where the data lives:** `owner` and `published_at` in the monolith table are the durable record. The broker holds messages until they are acknowledged.
- **If it goes wrong:**
  - Crash after intent, before publish: the relay publishes the row after restart. The monolith never sends it.
  - Crash after publish, before `published_at`: the row is published again. The service dedupes it.
  - Broker down: rows stay owner `service` and unpublished. The monolith sends nothing. Alert on the age of the oldest unpublished row.
  - The relay keeps running after any rollback until no unpublished `owner = 'service'` rows remain.

### Step 4: Service ingest

- **Starts when:** the service consumer receives a message from the notification topic.
- **What it does:** inserts the row into the service `notifications` table with `ON CONFLICT (id) DO NOTHING`. It copies `attempts` and `first_attempt_at` from the message. It stores the row as `queued` with `next_attempt_at = now()`. It acks the message only after that commit.
- **Table columns:** `id` (primary key), `type`, `email`, `payload`, `status` (`queued`, `sending`, `sent` or `failed`), `attempts`, `next_attempt_at`, `lease_until`, `first_attempt_at`, `accepted_at`, `created_at`.
- **Unknown type or schema version:** the service cannot render the row. It still inserts it. In the same transaction it sets the row to `failed`, writes a page intent, and writes a `failed` event to the outbox. Nothing is sent.
- **Where the data lives:** the service database only.
- **If it goes wrong:**
  - Redelivered message: the insert does nothing, and the message is acked.
  - Crash after commit, before ack: the message is redelivered and the insert does nothing.
  - Broker down: the consumer is idle, but queued rows still send.

### Step 5: Service claim

- **Starts when:** a polling loop on every service instance runs every 5 seconds. Ingest does not hand rows to the loop. The loop finds them. The 5-second interval is this plan's choice. It matches the monolith loops.
- **What it does:** finds rows that are `queued` with `next_attempt_at <= now()`, or `sending` with an expired lease. It locks them with `FOR UPDATE SKIP LOCKED`, so several instances are safe. Then, for each row, in this order:
  1. If `first_attempt_at` is more than 20 hours old and the row is not terminal, set it to `failed`, write a page intent in the same transaction, and do not send. The 24-hour MailRelay key window may have passed, so the row must never be sent again.
  2. If `attempts` is already 5, the last attempt crashed. Set it to `failed`, write a page intent in the same transaction, and do not send.
  3. Otherwise set status `sending`, add 1 to `attempts`, set `first_attempt_at` if it is unset, and set a lease. This commit happens before the send.
- **The clock:** the 20-hour guard measures from the row's first MailRelay send attempt, wherever that attempt happened. Enqueue time is not used. A row that has never been sent has no clock. Time it spends in the broker, the service queue, or the monolith does not count, because MailRelay has no key for it yet.
- **Attempts count at claim.** A crash mid-send therefore uses one attempt. See the open questions.
- **Where the data lives:** the service table.
- **If it goes wrong:**
  - Crash during the send: the row stays `sending`. When the lease expires, the claim takes it again with the same key.
  - Lease expires while the first send is still running: the second send uses the same key. MailRelay drops it if the first was accepted.

### Step 6: Service send and outcome

- **Starts when:** a claim in step 5 succeeds.
- **What it does:** renders the subject and body from the service's own copy of the templates, then calls MailRelay with `idempotency_key = id`.
  - On success, one transaction sets status `sent`, sets `accepted_at` to now, and writes a `sent` event to the outbox.
  - On failure (MailRelay error, timeout, or render error): if `attempts >= 5`, one transaction sets status `failed`, writes a `failed` event, and writes a page intent. Otherwise the row goes back to `queued` with `next_attempt_at = now() + [1, 2, 4, 8][attempts - 1]` minutes. Retries span about 15 minutes, as today.
- **Where the data lives:** the service table and the outbox.
- **If it goes wrong:** a crash between the send and the outcome leaves the row `sending`, and step 5 handles it. MailRelay 5xx responses, timeouts, and accept-then-lost-reply all take the failure path. The retry uses the same key, so MailRelay drops a send it already accepted.

### Step 7: Service outbox and pager

- **Starts when:** the outbox loop runs continuously in the service. The pager job runs on a schedule.
- **What it does:** the outbox loop publishes status events `{id, status: sent or failed, accepted_at, attempts}` to the status topic. The pager job reads unsent page intents, pages on-call with the same paging call the monolith uses today, and marks each intent sent.
- **Where the data lives:** the outboxes and page intents, in the service database.
- **If it goes wrong:** if the broker is down, events and page intents wait in their outboxes. A crash between paging and marking can page twice. That is acceptable, because paging is not user-facing.

### Step 8: Monolith status consumer

- **Starts when:** the monolith receives a status event on the status topic.
- **What it does:** runs `UPDATE notifications SET status = ?, attempts = ? WHERE id = ? AND owner = 'service' AND status = 'pending'`, copying `status` and `attempts` from the event. It acks the event after the commit.
  - It does not copy `accepted_at`, because the monolith has no such column. The latency gate reads it from the service database.
  - It does not page, because the service has already written the page intent.
- An event for a row that is not pending matches nothing and is a no-op. Terminal states are set once.
- Until an event arrives, the monolith row shows `pending`. That is the correct support view.
- **Ordering:** an event cannot arrive before owner is `service`. The service produces an event only after it ingests a message, and the monolith publishes that message only after it commits owner `service`. The status update does not touch `published_at`, so the two can land in either order without loss. If the event lands first, the row is terminal and the retry skips it. If it lands after the retry has read the row but before the publish, the repeat message is a no-op at ingest.
- **If it goes wrong:** if the consumer crashes before the ack, the event is redelivered. The second update matches nothing.

## What happens when things fail

| Failure | What happens | Notes |
|---|---|---|
| Monolith crashes after the intent commit, before publish | The relay publishes the row after restart. The monolith never sends it. | |
| Monolith crashes after publish, before `published_at` | The row is published again. The service dedupes it. | |
| Monolith crashes mid-send (monolith-owned row) | The transaction rolls back. The row returns to `NULL` and is sent again with the same key. | MailRelay drops it if it was already accepted within 24 h. |
| MailRelay error or timeout (monolith) | Handled as today: attempts, backoff, then failed and paged after attempt 5. | The key makes the retry safe. |
| Broker down (monolith side) | Relay rows stay `owner = service` and unpublished. The monolith sends nothing. | Alert on the age of the oldest unpublished row. |
| Broker down (service side) | The consumer is idle. Queued rows still send. | Status events and page intents wait in their outboxes. |
| Broker redelivers a message | The service insert does nothing, and the message is acked. | |
| Service crashes after ingest commit, before ack | The message is redelivered. The insert does nothing. | |
| Service crashes during send | The lease expires, and the row is claimed again with the same key. | |
| Lease expires while the first send is still running | The second send uses the same key. MailRelay drops it if the first was accepted. | |
| Crash on the 5th attempt (the claim finds attempts at 5) | The row is marked failed and paged. It is not sent. | Bounds poison rows. |
| Unknown type or schema version at ingest | The row is marked failed and paged, with a `failed` event. Nothing is sent. | |
| Render error in the service | Counts as a failed attempt. Same backoff and failure path as a MailRelay error. | |
| MailRelay returns 5xx | Backoff. After attempt 5, the row is failed and paged. | |
| MailRelay timeout or accept-then-lost-reply | The retry uses the same key. MailRelay drops it if it was already accepted. | |
| MailRelay down for a long time | About 15 minutes of backoff, then failed and paged. | |
| First MailRelay attempt more than 20 h ago, not terminal | Marked failed and paged. Never re-sent, because the key window is 24 h. | See the open questions: the 20-hour guard. |
| Status event arrives before `published_at` is set | The status update does not touch `published_at`. The row is terminal, so the retry skips it. | |
| Status event or page intent cannot be published | It stays in its outbox until it can be published. | Alert on the age of the oldest unpublished item in each outbox. |
| Flag read fails on one monolith instance | That instance uses `monolith` for every type. It may claim `NULL` rows of a service-routed type, and it may send a row whose flag reads `service`. The row lock and the owner value still give each row one owner, so the relay on another instance cannot claim the same row. | The monolith can always send, so this is kept as is. |
| Flag changed | The change reaches every instance within 10 s. The 5 s loop acts on it, so a flip takes effect within about 15 s. Rows already owned do not move. | |
| Service is broken after a flag rollback | Owned rows wait for the service, or for the 20-hour guard to fail and page them. The monolith cannot take them back. | See the open questions. |
| Either database restored from backup | Can roll state back and cause re-sends. | Restore procedures check `owner` and `status` before the service or the monolith resumes sending. |

**Paging.** Monolith-owned failed rows are paged by the monolith at attempt 5, as today. Service-owned failed rows are paged by the service pager job from page intents. Only the owner's side writes a row's failure, and the pager job reads only intents the service wrote, so no row is paged by both sides. A monolith crash after paging and before its commit can page twice. That is today's behavior and is unchanged.

**Residual risks.**

- The MailRelay key window is 24 h. A duplicate is possible only if a row's outcome is unknown after 24 h. The 20-hour guard turns that case into a page, not a duplicate.
- Restoring either database from a backup can roll state back and cause re-sends. Check `owner` and `status` before the service or the monolith resumes sending.
- Status events and page intents depend on their outboxes. Alert on the age of the oldest unpublished item in each.

## Rollout

These steps are how we ship and move traffic. They are separate from how the system runs. Ship them in this order.

1. **Key and per-row commit on the existing worker.**
   - **Starts when:** the monolith build with this change is deployed.
   - **What changes:** each send passes `idempotency_key = row.id`. The worker commits after each row instead of after each batch. Nothing else changes.
   - **Data:** the monolith table, unchanged.
   - **If it goes wrong:** a crash after MailRelay accepts but before the commit re-sends that row with the same key, and MailRelay drops it. A timeout is handled as today.
   - **Rollback:** redeploy the previous build. Old sends with a key are harmless.

2. **Ownership columns and claim rules.**
   - **Starts when:** an additive migration adds `owner`, `published_at` and `first_attempt_at`, all `NULL` by default. Then the new worker is deployed. Then the three `notifications.route.*` flags are created, each set to `monolith`.
   - **What changes:** the monolith claim in step 2 of the sending steps, which sets `owner` and `first_attempt_at`.
   - **Data:** nothing moves.
   - **If it goes wrong:** mixed versions are safe. Old instances process `NULL` rows without writing `owner` or `first_attempt_at`, and the new code still claims them. Old instances do record attempts, so a row may have attempts above 0 and no `first_attempt_at`. The relay handles that case as step 3 describes. The relay is not running yet. A crash mid-send returns the row to `NULL`, and it is re-sent with its key.
   - **Rollback:** not needed, since the migration is additive.

3. **Relay, dark until a type routes to the service.**
   - **Starts when:** the relay runs on every monolith instance. No row is service-routed yet, so it does nothing. Its details are in step 3 of the sending steps.

4. **Status consumer, dark.**
   - **Starts when:** the monolith subscribes to the status topic. Nothing arrives until a type moves.

5. **Build the Notification Service, with no live traffic.**
   - **Starts when:** the service is deployed to its own runtime, with its own database. No flag routes to it yet.
   - **What it contains:** ingest, render, claim, send, outcome, outbox and pager, as in the sending steps.
   - **Render:** the templates are copied into the service. Golden tests show byte-identical subject and body against the monolith for all three types. The golden test runs in CI on every change and fails if the two copies differ. Until step 11, a template change goes into both copies in the same release.
   - **Data:** only in the service database.

6. **Staging rehearsal and fault injection. This is the gate for step 7.**
   - **Starts when:** step 5 is in staging.
   - **Traffic:** synthetic, at production rates of 40,000, 12,000 and 1,500 per day for `shipping_update`, `order_confirmed` and `password_reset`.
   - **Tests:**
     - `kill -9` the monolith and the service at each boundary: after claim, after publish, after ingest commit, and after accept.
     - Force broker redelivery.
     - Make the MailRelay fake return 5xx, timeouts, and accept-then-lost-reply.
     - Measure end-to-end flag flip time, including the 5 s poll and the 10 s propagation.
     - Roll back mid-flight, with rows owned by both sides.
     - Simulate a 30-minute broker outage.
     - Run reconciliation at the end of each test.
   - **Gate:** zero duplicate accepts per `id` on the MailRelay fake. Every committed row reaches a terminal state, confirmed by reconciliation. Any failing test blocks step 7.

7. **Move `shipping_update`.**
   - **Starts when:** step 6 passes.
   - **What changes:** set `notifications.route.shipping_update = service` in production. New rows are claimed by the relay and sent by the service. Rows already owned by the monolith finish there.
   - **Hold:** at least 3 days. The hold is done when all of these hold:
     - no duplicate reports from support;
     - every service-owned row reaches a terminal state (reconciliation);
     - failure and paging rates are within the monolith baseline;
     - the oldest unpublished row is under the alert threshold.
   - **Rollback:** set the flag back to `monolith`. It takes effect within a minute. Rows already owned by the service are not moved or re-sent. They drain on the service, and the relay keeps running. The service may not be scaled to zero until `owner = 'service' AND status IN ('queued','sending')` returns zero rows.

8. **Move `order_confirmed`.**
   - **Starts when:** step 7 has held for 3 days and passed.
   - **What changes:** same mechanics and rollback as step 7.
   - **Latency measurement starts here.** Enqueue-to-MailRelay latency is `accepted_at - created_at`. Clock sync between the database and service hosts must keep skew well below 60 s.

9. **Hold `order_confirmed` and check the latency gate.**
   - **Starts when:** step 8 is live.
   - **Hold:** 3 days.
   - **Gate:** p99 enqueue-to-MailRelay under 60 s on `order_confirmed`, service-owned rows only.
   - **If it fails:** do not start step 10. Investigate and rerun the hold.

10. **Move `password_reset`.**
    - **Starts when:** steps 8 and 9 have passed.
    - **What changes:** `password_reset` rows follow the same path.
    - **Rollback:** the same flag flip as before. This is the most latency-sensitive type, so run the rollback drill in staging before production.

11. **Decommission the old worker.**
    - **Starts when:** `password_reset` has run on the service for 7 days, and this query returns zero: `status = 'pending' AND owner IN (NULL, 'monolith')`.
    - **Actions:**
      - Remove the monolith worker loop and its claim code.
      - Keep the old worker deployable until `password_reset` has run on the service for 7 days. Do not delete it earlier.
      - Remove the `notifications.route.*` flags. The relay then claims every unclaimed row, since all types now route to the service.
      - Keep the relay and the status consumer. They are the only path to the service.
    - **If it goes wrong:** if pending monolith-owned rows remain, do not remove the worker. Investigate first.
    - **After this step,** rollback to the monolith is no longer possible.

## Open questions

Decisions for the owner to confirm:

1. **Crash counts as an attempt.** The service increments `attempts` at claim, so a crash mid-send uses up an attempt. Today's worker rolls back and does not count it. Counting it bounds poison messages, but it can fail a notification sooner than today. Confirm.
2. **p99 gate scope.** Does the 60 s gate include retried sends? Any send that needs a retry takes at least 1 minute. If more than 1% of sends retry, p99 fails regardless of pipeline speed. Confirm whether to gate on all accepted rows or on first-attempt rows only, and report both.
3. **Personal data on the broker.** Email and payload travel on the broker, which billing and search also use. The service cannot read the monolith database to look them up. Confirm the data policy allows this, or encrypt the email field.
4. **20-hour guard.** Rows whose first attempt is more than 20 hours old and not terminal are failed and paged, never re-sent. Confirm this trade-off.
5. **Service broken after a flag rollback.** Owned rows stay with the service. The plan gives the monolith no way to take them back, so they wait for the service or for the 20-hour guard. One option is a monolith takeover that re-sends with the same key within 24 hours. MailRelay would drop it if the first send was accepted. That needs a decision and is not in this plan.
6. **Who runs reconciliation.** The plan does not say who runs it in staging or during the holds in steps 7 to 10, or who signs off on the result. Name an owner.

Gaps the plan does not settle yet:

7. **Errors other than MailRelay errors.** Today's worker catches only MailRelay errors. The plan does not say what the monolith claim does with any other exception.
8. **Flag store.** The plan uses `flags.get(name)`. The brief does not name the store behind it.
9. **Topic names.** The notification topic and the status topic are named here by role only. Their names are set during the build.
10. **Paging path.** How the service reaches the paging system is a build question.
11. **Template sync beyond CI.** The golden test catches differences. How the two template copies are updated together is a build detail.