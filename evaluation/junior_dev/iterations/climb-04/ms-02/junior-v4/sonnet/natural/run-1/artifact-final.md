# Plan: extract notifications into a Notification Service

## Summary

Today the monolith inserts a `notifications` row inside the caller's transaction. A worker thread on every monolith instance then sends the pending rows through MailRelay. We move sending into a separate Notification Service with its own database. The monolith still records every notification first. When a row is inserted, a flag decides whether the old worker or the service will send it. The broker carries requests to the service and results back. Types move one at a time, and a flag flip rolls a type back.

## Terms

- **Caller:** business code (checkout, carrier webhook, password reset). It calls `enqueue_notification(tx, ...)` inside its own transaction. The row exists only if that transaction commits.
- **Old worker:** `run_worker`, a thread on each monolith instance. Every 5 s it locks up to 50 due `pending` rows (`FOR UPDATE SKIP LOCKED`), sends each, and commits once per batch. Success makes a row `sent`. A failure keeps it `pending` with a later `next_attempt_at`, or makes it `failed` after attempt 5 and pages on-call with `alerts.page_oncall`. If an instance dies before the commit, the whole batch is sent again.
- **MailRelay:** the email provider. `send()` takes an optional `idempotency_key`. If MailRelay accepted the same key in the last 24 h, it drops the new send and returns success. "Accepted" means `send()` returned success.
- **Broker:** the existing at-least-once message broker. A publisher gets a confirmation once the broker has stored its message. A consumer acks when done. An unacked message is redelivered after 30 s, possibly to another consumer.
- **Flag:** `flags.get(name)` in the monolith. A change reaches every monolith instance within 10 s.
- **Outbox:** rows in a database that wait to be published. A row is marked published only after the broker confirms.
- **Route:** a column on each notification, `monolith` or `service`. It names the one side that sends the row.

## How the system runs

Rules that hold at every step:

1. **One owner per row, fixed at insert.** `enqueue_notification` sets `route` from the flag, in the caller's transaction. The route never changes afterwards. The old worker sends only `route='monolith'` rows. The service sends only rows that reached it through the broker, which are exactly the `route='service'` rows. A flag flip affects only rows inserted after it.
2. **MailRelay is the last duplicate guard.** Every send, on either side, passes `idempotency_key=<notification id>`. A second send within 24 h is dropped.
3. **The monolith table stays the first record and the record of status.** The service reports the final status (`sent` or `failed`) back over the broker. Neither database is ever read by the other side.
4. **Both directions use an outbox.** The monolith publishes rows with `published_at IS NULL`. The service publishes results with `result_published_at IS NULL`. Consumers write to their own database first and ack afterwards. Duplicates do nothing, because of `id` uniqueness on the service and `WHERE status='pending'` on the monolith.
5. **Retries are unchanged.** 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5. After the fifth failure the row is `failed` and on-call is paged.
6. **23 h guard.** Before every send, the owner checks the row's age. If it is over 23 h old and not final, it is not sent. It is marked `failed` and on-call is paged, because MailRelay may have forgotten an earlier send and a human must check. The service reports this `failed` like any other result.

Broker topics: `notifications.requested` (monolith to service) and `notifications.result` (service to monolith).

Messages:
- Requested: `{id, type, user_id, email, payload, created_at}`. The service picks the template from `type` and sends to `email`. `user_id` is only for traceability.
- Result: `{id, status: sent|failed, attempts}`.

The Notification Service has four parts:
- **Consumer:** reads `notifications.requested`. In one transaction it runs `INSERT ... ON CONFLICT (id) DO NOTHING`, then acks. It does not send, so it acks well inside 30 s.
- **Sender loop:** polls every 1 s and claims up to 50 due rows. A row is due when `status='pending'`, `next_attempt_at <= now()`, and its lease is empty or expired. The loop claims with `FOR UPDATE SKIP LOCKED` and applies the 23 h guard. It then sets `lease_until = now() + 2 min` (longer than the MailRelay timeout) and commits, so no transaction stays open during the network call. It renders the template, calls `mailrelay.send(..., idempotency_key=id)`, and commits that one row's outcome: `sent`, a retry with the next backoff, or `failed` on attempt 5. `attempts` changes only when an outcome is committed. After a crash the lease expires, and the re-send uses the same attempt number and key. A template render error counts as a failed attempt.
- **Result publisher:** polls every 1 s and publishes `{id, status, attempts}` for final rows with `result_published_at IS NULL`. It sets that column only after the broker confirms.
- **Pager loop:** pages on-call for `failed` rows with `paged_at IS NULL`, then sets `paged_at`. A crash between the page and the update can page twice, which is acceptable.

Service table `notifications`: `id PK, type, email, payload, created_at, status, attempts, next_attempt_at, lease_until, result_published_at, paged_at, received_at`.

The monolith also runs two small loops:
- **Publisher:** every 1 s it selects `route='service' AND published_at IS NULL AND status='pending'` (`FOR UPDATE SKIP LOCKED`, oldest first). It publishes each row on its own. After the broker confirms, it sets `published_at`. A row the broker rejects stays unpublished and is tried again on the next loop, and it does not block other rows. A crash after the confirmation causes a re-publish, which the service ignores by `id`. It selects by `published_at IS NULL`, not by time, so a late-committing transaction is still found.
- **Result consumer:** runs `UPDATE notifications SET status=$s, attempts=$a WHERE id=$id AND status='pending'`, then acks.

## Rollout steps

Each step lists what starts it, what it does, where the data lives, and what happens on failure.

| Day | Event |
|---|---|
| 0 | `shipping_update` moves (step 7). |
| 3 or later | `order_confirmed` moves (step 8). |
| 6 or later | `password_reset` moves (step 9), after 3 days on `order_confirmed` and the p99 gate. |
| 13 or later | Old worker removed (step 10), 7 days after `password_reset` moves. |

### Step 1. Add the idempotency key to the old worker

- **Starts when:** first, with no dependencies. It ships alone.
- **Does:** `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`.
- **Data lives in:** the monolith `notifications` table, as today. Only the key is new.
- **If it goes wrong:** after a crash before the batch commit (the cause of about 30 duplicate emails a week), the rows are re-sent and MailRelay drops the repeat. A timed-out send that was actually accepted is also deduplicated on retry. MailRelay down behaves as today: backoff, then `failed` and a page.
- **Done when:** the rollout is complete on all instances and support-reported duplicates fall to about zero. Hold step 2 until then.

### Step 2. Monolith schema change and route-aware worker (still all monolith)

- **Starts when:** step 1 is deployed everywhere.
- **Does:**
  - Adds `route text NOT NULL DEFAULT 'monolith'` and `published_at timestamptz NULL`, plus a partial index on `(created_at) WHERE route='service' AND published_at IS NULL AND status='pending'`.
  - `enqueue_notification` keeps its signature and inserts `route` from the flag `notifications.route.<type>`. If the flag is missing or errors, it uses `monolith`.
  - The worker query adds `AND route='monolith'` and applies the 23 h guard.
  - Creates the three route flags, all set to `monolith`.
- **Data lives in:** the monolith database. Nothing leaves it.
- **If it goes wrong:** during a rolling deploy, old instances insert rows with the default `monolith` and old workers select everything. This is safe because no `service` row exists yet. No flag may be flipped until every instance runs the route-aware worker. Check this before step 7. If the flag service is down, rows fall back to `monolith`. Add the columns with a default and create the index concurrently, so the migration stays cheap.

### Step 3. Build the Notification Service and its database

- **Starts when:** it can be built in parallel with steps 1 and 2. Production deploy waits for step 2.
- **Does:** builds the four parts above. It moves the templates for the three types into the service and compares its output against the monolith's `templates.render` for sample payloads of each type.
- **Data lives in:** the service database. It receives nothing yet.
- **If it goes wrong:** test these in staging with a fake MailRelay and a test broker.
  - A kill mid-send leads to a re-send with the same key and no duplicate.
  - The same message delivered 5 times gives one row and one send.
  - If the service database is down, the consumer does not ack and the broker redelivers.
  - MailRelay down gives 5 attempts, then `failed` and a page.
  - A malformed message (unparseable, missing field, or a `type` with no template) goes to a dead-letter queue and pages. The monolith row stays `pending` and the 60 min alert in step 4 fires.

### Step 4. Monolith publisher and result consumer (deployed dark)

- **Starts when:** step 3 is in production. This is safe because no row has `route='service'`.
- **Does:** deploys the publisher and result consumer described above.
- **Data lives in:** `published_at` and `status` in the monolith database. Out to the service go id, type, user id, email, payload and created_at. Back come id, status and attempts.
- **If it goes wrong:**
  - Broker down: rows stay unpublished and are retried, so nothing is lost. Alert if the oldest unpublished row is over 2 min old.
  - Result lost or delayed: the row stays `pending` and is never re-sent. Any `route='service'` row still `pending` after 60 min pages on-call. The alert changes no row, because the monolith cannot see the service database and a human must check.
  - Result consumer down: the broker redelivers.

### Step 5. Production canary

- **Starts when:** step 4 is deployed.
- **Does:** adds a test-only type `service_canary`, sent every few minutes to an internal mailbox by a cron job. Its flag is `service`. The three real types are untouched. Each canary runs the whole path: monolith row, publisher, broker, service, MailRelay with key, result, monolith `sent`.
- **Data lives in:** both databases, as designed.
- **If it goes wrong:** run these drills in business hours. Stop the service for 10 min and check rows are sent after restart without duplicates. Pause the consumer so messages are redelivered. Block MailRelay and see 5 attempts, then `failed` and a page. Kill the service between the MailRelay call and the commit and check that one email arrives.
- **Done when:** all drills pass and the enqueue-to-MailRelay latency (from `created_at`) is recorded per type.

### Step 6. Dashboards, alerts and rollback runbook

- **Starts when:** before the first move. This is documentation and dashboards only.
- **Does:** per type, shows p50 and p99 enqueue-to-MailRelay latency (retries included), the unpublished backlog, the service pending backlog, the failed count, support-reported duplicates, and the share of `route='service'` rows `pending` after 60 min. It writes the rollback runbook below and rehearses it on `service_canary`.

### Step 7. Move `shipping_update` (40,000/day), then soak 3 days

- **Starts when:** steps 1 to 6 are done and every monolith instance runs the route-aware worker. Flip `notifications.route.shipping_update` to `service`. It takes effect within 10 s.
- **Does:** new rows are inserted with `route='service'` and published. Rows inserted before the flip stay with the old worker. Each row has exactly one owner.
- **Data lives in:** the monolith row (`pending` until the result arrives) and the service row (attempts, next attempt time).
- **If it goes wrong:** see "Failures" below. For any serious problem, roll back.
- **Moves on when, all of:** 3 full days have passed. No `route='service'` row is `pending` beyond its retry window. No duplicate is traced to the service. Monolith CPU and database connection use have dropped. Every `failed` row paged on-call. Restart the 3-day clock after any fix that changes the sending path.

### Step 8. Move `order_confirmed` (12,000/day), then soak 3 days and check latency

- **Starts when:** step 7's conditions are met. Flip `notifications.route.order_confirmed` to `service`.
- **Does, data and state:** same as step 7. Rollback affects only this type.
- **Moves on when:** the step 7 conditions hold, and **p99 enqueue-to-MailRelay latency on `order_confirmed` is under 60 s**.
- **How it is measured:** `MailRelay accepted time - created_at` over every notification of the type in the window, retries included. A first-attempt failure alone pushes a notification past 60 s, because the first backoff is 60 s. So more than 1% of notifications needing a retry fails the gate. That strictness is intended, because `password_reset` has the same requirement.
- **If the gate fails:** find the cause (publisher interval, consumer lag, sender capacity, MailRelay failure rate) and fix it. Do not move `password_reset`. The clock restarts after any pipeline fix.

### Step 9. Move `password_reset` (1,500/day), then soak 7 days

- **Starts when:** step 8's conditions are met. Flip `notifications.route.password_reset` to `service`.
- **Does, data and state:** same as step 7. Add alerts for p99 above 45 s, for any `password_reset` row unpublished for over 30 s, and for any still `pending` after 2 min.
- **If it goes wrong:** if the broker or service is slow or down, roll back at once. New resets go to the monolith and in-flight ones finish on the service. During a MailRelay outage the 60 s target cannot hold, as before. Keep the old worker deployed.
- **Moves on when:** 7 days have passed with the health checks and p99 gate holding.

### Step 10. Remove the old worker

- **Starts when:** step 9's soak is finished, there are zero `route='monolith'` rows `pending`, and all three flags have been `service` for the required periods.
- **Does:** removes `run_worker`, `_deliver` and the monolith template code for these types. `enqueue_notification` writes `route='service'` unconditionally and the flags are retired. The publisher, result consumer, table and `enqueue_notification` stay.
- **If it goes wrong:** flag rollback no longer exists. Redeploy the previous monolith release, which still has the worker and flags, only if the service cannot be fixed quickly. During the deploy, old and new instances can both insert rows, but each row still has one owner.

## Rollback (any time after step 7, per type)

- **Action:** set `notifications.route.<type>` back to `monolith`. It takes effect within 10 s, inside the one-minute requirement.
- **New notifications:** rows inserted after the flip get `route='monolith'` and are sent by the old worker, with the key.
- **Rows already in flight:** rows with `route='service'` keep their owner and finish on the service, whether unpublished, in the broker, mid-retry or mid-send. The service keeps running. Nothing is moved, so nothing is lost or sent twice.
- **Roll forward:** flip the flag back to `service`. Rows already owned by the monolith stay there.
- **Emergency, service dead and rows stuck:** an operator stops the service's sender loop for that type, then hands stuck rows (`route='service'`, `status='pending'`, under 23 h old) to the monolith with `UPDATE ... SET route='monolith', published_at=NULL`. MailRelay's key drops any repeat of an already-accepted send. These rows get a fresh attempt count, a known deviation. Rows over 23 h old are marked `failed` and paged instead.

## Failures

| Failure | Handled by | Result |
|---|---|---|
| Monolith crashes before the enqueuing transaction commits | Row never exists | No notification, as today |
| Monolith crashes after broker confirms, before `published_at` | Row is re-published | Service ignores it by `id` |
| Broker down | Both outboxes keep their rows | Delayed, not lost; alerts fire |
| Broker redelivers a message | `ON CONFLICT (id)` and MailRelay key | One email |
| Service crashes after MailRelay accepts, before commit | Lease expires, re-send with same key | One email |
| Service crashes after commit, before result is published | Result outbox republishes | Monolith consumer ignores repeats |
| Service crashes after `failed`, before the page | Pager loop reads `paged_at IS NULL` | Page not lost |
| MailRelay down or timing out | 5 attempts, 1/2/4/8 min backoff | Then `failed` and a page |
| Malformed requested message | Dead-letter queue and page | Monolith row stays `pending`; 60 min alert; a human decides |
| Result message lost | 60 min pending alert | On-call investigates; no automatic resend |
| Flag flip during in-flight work | Route stored on the row | No row changes owner |

## Open questions

- Who flips the routing flags, and with which tool? The platform's flag tooling is assumed.
- What reads `notifications.status` in the monolith today (support tools, other code)? Not known. It is kept up to date as the brief requires, and the 60 min alert depends on it.
- Which broker product is it, and does it offer a dead-letter queue? Not stated.
- Does MailRelay send the email itself or hand it on? Not stated. The plan relies only on "accepted" meaning `send()` returned success.
- How does the service page on-call? `alerts.page_oncall` lives in the monolith code. Whether the service can use the same paging system is not stated.
