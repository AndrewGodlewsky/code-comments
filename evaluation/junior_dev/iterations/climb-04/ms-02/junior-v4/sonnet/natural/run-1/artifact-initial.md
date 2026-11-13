# Plan: extract notifications into a Notification Service

## Design summary

These rules hold for every step below.

1. **One owner per notification, fixed at insert time.** `enqueue_notification` stamps each row with `route` (`monolith` or `service`) from a flag, in the caller's own transaction. The route never changes afterwards. The old worker only sends `route='monolith'` rows. The service only sends rows that reached it through the broker, which are exactly the `route='service'` rows. Cutover and rollback therefore never create two owners for one row. A flag flip only affects rows inserted after it.
2. **MailRelay is the final duplicate guard.** Every send, on either side, passes `idempotency_key=<notification id>`. Within 24 h, a crash or redelivery that causes a second send is dropped by MailRelay, which returns success.
3. **The monolith `notifications` table stays the first record and the system of record for status.** For service-routed rows the service reports the terminal status (`sent` or `failed`) back over the broker. The monolith never reads the service DB and the service never reads the monolith DB.
4. **Both directions use an outbox with idempotent consumers.**
   - Monolith to service: rows with `published_at IS NULL`, published until the broker confirms.
   - Service to monolith: result rows with `result_published_at IS NULL`, published until the broker confirms.
   - Consumers write to their own DB first, then ack. Duplicates are no-ops because of `id` uniqueness and `WHERE status='pending'`.
5. **Retry policy is unchanged on both sides.** There are 5 attempts, with waits of 1, 2, 4 and 8 minutes before attempts 2 to 5. After the fifth failure the row is marked `failed` and on-call is paged. The whole retry window is about 15 minutes plus polling, well inside MailRelay's 24 h key window.
6. **24 h guard.** If a non-terminal row is more than 23 h old, nobody resends it. It is marked `failed` and on-call is paged. By then MailRelay may no longer remember an earlier accepted send, and a human must check.

Broker topics:

- `notifications.requested`: monolith to service.
- `notifications.result`: service to monolith.

Message shapes:

- Requested message: `{id, type, user_id, email, payload, created_at}`.
- Result message: `{id, status: sent|failed, attempts}`.

## Calendar

| Day | Event |
|---|---|
| 0 | `shipping_update` moves to the service (step 7). |
| 3 or later | `order_confirmed` moves (step 9). |
| 6 or later | `password_reset` moves (step 11). It needs 3 days on `order_confirmed` and the p99 gate under 60 s. |
| 13 or later | Old worker removed (step 12), 7 days after `password_reset` moves. |

---

## Step 1. Add the idempotency key to the old worker

- **Starts when:** First, with no dependencies. This ships alone, before any type moves.
- **Change:** In `_deliver`, call `mailrelay.send(to=..., subject=..., body=..., idempotency_key=row.id)`.
- **Data moves:** Only the key goes to MailRelay. Nothing else changes.
- **State lives in:** The monolith `notifications` table, as today.
- **If something fails:**
  - **Crash after MailRelay accepts but before the batch commit.** This is the cause of today's roughly 30 duplicate emails a week. The rows stay `pending` and are re-sent on the next poll, a few seconds later. MailRelay drops the repeat and returns success, so the row becomes `sent` and no duplicate email goes out.
  - **MailRelay timeout where it actually accepted the send.** The retry (1 to 8 minutes later) carries the same key, so it is deduplicated too.
  - **MailRelay down.** Behaviour is unchanged: backoff, then `failed` and a page.
- **Exit check:** Support-reported duplicates drop from about 30 a week to about zero. Hold step 2 until the rollout is complete on all instances.

## Step 2. Monolith schema change and a route-aware worker (still 100% monolith)

- **Starts when:** Step 1 is deployed everywhere.
- **Changes:**
  - Add columns `route text NOT NULL DEFAULT 'monolith'` and `published_at timestamptz NULL`. Add a partial index on `(created_at) WHERE route='service' AND published_at IS NULL AND status='pending'`.
  - `enqueue_notification` keeps its signature. It now also inserts `route = flags.get("notifications.route." + ntype)`, defaulting to `monolith` if the flag is missing or errors.
  - The worker query gains `AND route = 'monolith'`.
  - Create the flags `notifications.route.shipping_update`, `.order_confirmed` and `.password_reset`, all set to `monolith`.
- **Data moves:** Nothing leaves the monolith. Behaviour is identical to step 1.
- **State lives in:** The monolith DB.
- **If something fails:**
  - **Rolling deploy leaves some instances on the old code.** Old instances insert rows without `route`, which get the default `monolith`. Old workers select everything. That is safe because no `service` row can exist yet. **Rule: no flag may be flipped until every instance runs the route-aware worker.** Check the deployed version on all instances before step 7.
  - **Flag service unavailable.** `enqueue` falls back to `monolith`, so no row is stranded.
  - **Migration is locked or slow.** Add the columns with a default, which is cheap. Create the index concurrently.

## Step 3. Build the Notification Service and its own database (receiving nothing yet)

- **Starts when:** Can be built in parallel with steps 1 and 2. Deployment to production waits for step 2.
- **Service DB table `notifications`:** `id PK, type, email, payload, created_at (from the monolith), status, attempts, next_attempt_at, lease_until, result_published_at, paged_at, received_at`.
- **Components:**
  - **Consumer** of `notifications.requested`. In one transaction it does `INSERT ... ON CONFLICT (id) DO NOTHING`. It acks after the commit. It does no sending, so it acks well inside the 30 s limit.
  - **Sender loop:**
    - It claims due rows (`status='pending' AND next_attempt_at <= now()`) with `FOR UPDATE SKIP LOCKED`.
    - It sets `lease_until = now() + 2 min`, which must be longer than the MailRelay timeout, and commits. No transaction stays open during the network call.
    - It renders the template with the service's own copy.
    - It calls `mailrelay.send(..., idempotency_key=id)`.
    - It then commits that one row's outcome: `sent`, a retry with `attempts` and `next_attempt_at` using 1/2/4/8 min, or `failed` on attempt 5.
    - Commits are per row, not per batch.
  - **Result publisher:**
    - It publishes `{id, status, attempts}` for terminal rows where `result_published_at IS NULL`.
    - It sets `result_published_at` only after the broker confirms.
  - **Pager loop:** It pages on-call for `failed` rows where `paged_at IS NULL`, then sets `paged_at`. Paging is driven from the DB rather than called inline, so a crash after the commit cannot lose a page. A crash between the page and `paged_at` can page twice, which is acceptable.
- **Rendering:**
  - Move the templates for the three types into the service.
  - Run a golden-output comparison against the monolith's `templates.render` for sample payloads of each type.
  - Decision for new behaviour: a render exception counts as a failed attempt. It goes through the same backoff and ends in `failed` plus a page. In the monolith, an exception would roll back the whole batch and retry it every 5 s forever, which is worse.
- **Data moves:** Nothing yet.
- **If something fails (to be tested in staging with a fake MailRelay and a test broker):**
  - **Kill the service mid-send.** The lease expires and the row is re-sent with the same key, so there is no duplicate.
  - **Redeliver the same message 5 times.** There is one row and one send.
  - **Service DB down.** The consumer does not ack, so the broker redelivers after 30 s. Nothing is lost.
  - **MailRelay down.** The row goes through the 5-attempt backoff, then `failed` and a page.
  - **Malformed message.** It is rejected to a dead-letter queue with a page rather than redelivered forever.

## Step 4. Monolith publisher and result consumer (deployed dark)

- **Starts when:** Step 3 is deployed to production. Safe at any time because no row has `route='service'` yet.
- **Publisher** (a background loop on the monolith, cheap compared with rendering and sending):
  - Every 1 s it selects `route='service' AND published_at IS NULL AND status='pending'` with `FOR UPDATE SKIP LOCKED`, ordered by `created_at`.
  - It publishes to `notifications.requested`.
  - After the broker's confirmation it sets `published_at`. A crash between the confirmation and the commit leads to a re-publish, which the service dedupes by `id`.
  - It selects by the `published_at IS NULL` predicate, not by a time watermark, so a row from a long transaction that commits late is still found.
- **Result consumer** of `notifications.result`:
  - It runs `UPDATE notifications SET status=$s, attempts=$a WHERE id=$id AND status='pending'`.
  - It acks after the commit. Redelivery is a no-op.
- **Data moves:** Publisher: id, type, user id, email, payload and created_at leave the monolith. Consumer: only id, status and attempts come back.
- **State lives in:** `published_at` and `status` in the monolith DB. The broker holds in-transit data.
- **If something fails:**
  - **Broker down.** Publishing fails and rows stay `published_at IS NULL`. The publisher retries with backoff, and nothing is lost. Alert when the oldest unpublished row is older than 2 min. For `password_reset` this is the first sign of a latency problem.
  - **Monolith crash mid-publish.** See above: a re-publish is deduped by the service.
  - **Result lost or delayed.** The row stays `pending` and the monolith does not resend it, so no duplicates. Reconciliation alert: any `route='service'` row still `pending` after 60 min pages on-call. The monolith cannot look inside the service DB, so a human checks.
  - **Result consumer down.** The broker retains and redelivers results.

## Step 5. Production canary

- **Starts when:** Step 4 is deployed.
- **Change:** Add a test-only type `service_canary`, enqueued every few minutes by a cron job to an internal mailbox. Its flag is set to `service`, and none of the three real types are touched.
- **Data moves:** The full path runs once per canary: monolith table, publisher, broker, service DB, template, MailRelay with key, result, monolith status `sent`.
- **State lives in:** Both DBs, as designed.
- **If something fails:** Use the canary for a staged fault drill during business hours.
  - Stop the service for 10 min. Rows stay pending and are sent after it restarts, with no duplicates.
  - Pause the consumer so messages are redelivered.
  - Block MailRelay and confirm the sequence of 5 attempts, then `failed` plus a page.
  - Kill the service between the MailRelay call and the commit, and confirm a single email arrives.
- **Exit:** All drills pass and the end-to-end latency metric (enqueue to MailRelay acceptance, using `created_at`) is being recorded per type.

## Step 6. Define go/no-go gates and rollback runbook

- **Starts when:** Before the first move. This is documentation and dashboards only.
- **Dashboards and alerts per type:** p50/p99 enqueue-to-MailRelay latency, counting retries; unpublished backlog; pending backlog on the service; failed count; duplicates reported by support; share of `route='service'` rows still `pending` after 60 min.
- **Rollback runbook:** see "Rollback" below. Rehearse it on `service_canary`.

## Step 7. Move `shipping_update` (40,000/day)

- **Starts when:** Steps 1 to 6 are done and every monolith instance runs the route-aware worker. Flip `notifications.route.shipping_update` to `service`. It takes effect in the monolith within 10 s.
- **Data moves:** New `shipping_update` rows (from carrier webhooks) are inserted with `route='service'` and published. Rows inserted before the flip, or in the first 10 s on instances with the old flag value, stay with the monolith worker. That is fine because each row has exactly one owner.
- **State lives in:** The monolith row (`pending` until the result arrives) and the service row (attempts, next attempt time).
- **If something fails:**
  - **Service crash.** The lease expires, the row is re-sent with the same key, and there is no duplicate.
  - **Broker down.** Rows wait in the monolith outbox until the broker returns. Delivery is delayed, not lost.
  - **MailRelay down.** Retried on the service with the 1/2/4/8 min policy, then marked `failed` and on-call is paged. The result message sets the monolith row to `failed`.
  - **Redelivery.** Deduped by `id` in the service DB and by MailRelay's key.
  - **Any problem at all.** Flip the flag back; see "Rollback".

## Step 8. Soak `shipping_update` for at least 3 days

- **Starts when:** Step 7 is live.
- **Exit criteria, all required:**
  - 3 full days have passed.
  - No unresolved `route='service'` row is `pending` beyond its retry window.
  - No duplicate email is traced to the service.
  - Monolith checkout CPU and DB connection use have dropped.
  - Every `failed` row paged on-call exactly as before.
- **State lives in:** Dashboards. There is no data movement.
- **If something fails:** Fix forward if the defect is small, or roll back (below). Restart the 3-day clock after any fix that changes the sending path.

## Step 9. Move `order_confirmed` (12,000/day)

- **Starts when:** Step 8 exit criteria are met. Flip `notifications.route.order_confirmed` to `service`.
- **Data moves and state:** As in step 7. This type becomes the p99 evidence for the next gate.
- **If something fails:** As in step 7. Rollback affects only this type, and `shipping_update` stays on the service.

## Step 10. Soak `order_confirmed` for at least 3 days and check the latency gate

- **Starts when:** Step 9 is live.
- **Exit criteria, all required:**
  - 3 full days have passed.
  - The same health checks as in step 8 pass.
  - **p99 enqueue-to-MailRelay latency on `order_confirmed` is under 60 s.**
- **How to measure:** The metric is `mailrelay accepted time - created_at` over all notifications of the type in the soak window, including those that needed a retry. A first-attempt failure alone pushes a notification past 60 s (the first backoff is 60 s), so more than 1% of notifications needing a retry is enough to fail the gate. That is the intended strictness, because `password_reset` has the same requirement.
- **If something fails:** If p99 is over 60 s, find the cause (publisher poll interval, consumer lag, sender loop capacity, MailRelay failure rate) and fix it. Do not move `password_reset`. The clock restarts for any fix to the pipeline.

## Step 11. Move `password_reset` (1,500/day, p99 under 60 s)

- **Starts when:** Step 10 gates are met. Flip `notifications.route.password_reset` to `service`.
- **Data moves and state:** As in step 7. Add an alert on p99 above 45 s and on any `password_reset` row unpublished for more than 30 s or still `pending` for more than 2 min.
- **If something fails:**
  - **Broker or service slow or down.** The alerts above fire. Roll back immediately (below). New resets go to the monolith while in-flight ones finish on the service.
  - **MailRelay down.** Same retry policy as before. The 60 s requirement obviously cannot hold during a MailRelay outage, and it was equally unmet before.
  - **Crash or redelivery.** Same protections as before, with no duplicate email.
- Keep the old worker deployed.

## Step 12. Soak 7 days, then decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days with the health checks and p99 gate holding.
- **Preconditions before the removal deploy:**
  - There are zero `route='monolith'` rows in `pending`. The old worker can drain these in the preceding days.
  - All three flags have been `service` for the required periods.
- **Change:**
  - Remove `run_worker` and `_deliver` from the monolith.
  - `enqueue_notification` writes `route='service'` unconditionally, and the flags are retired.
  - Keep the publisher, the result consumer, the `notifications` table and `enqueue_notification` itself.
  - Drop the monolith's template code for these types.
- **If something fails:**
  - **Problem after removal.** The old flag-based rollback no longer exists, because the old worker is gone. Roll back by redeploying the previous monolith release, which still contains the route-aware worker and the flags. Do this only if the service itself cannot be fixed quickly.
  - **Instances mid-deploy.** Old instances still insert with the flag-driven route and still run the worker, while new ones insert `service`. Every row keeps a single owner, so this is safe.

---

## Rollback (any time after step 7, per type)

- **Action:** Set `notifications.route.<type>` back to `monolith`. It takes effect on every monolith instance within 10 s, which meets the one-minute requirement.
- **Effect on new notifications:** Rows enqueued after the flip get `route='monolith'` and are sent by the old worker, with the key.
- **Effect on rows already in flight:**
  - Rows with `route='service'` keep their owner and are finished by the service, whether they are unpublished, in the broker, mid-retry or mid-send. The service keeps running during a rollback.
  - Nothing is moved, so nothing is lost and nothing is sent twice. The old worker never selects these rows.
- **Roll forward again:** Flip the flag back to `service`. Rows already owned by the monolith stay there.
- **If the service itself is dead and in-flight rows are stuck (emergency only):**
  - An operator may hand stuck rows (`route='service'`, `status='pending'`, age under 23 h) to the monolith with `UPDATE ... SET route='monolith', published_at=NULL`, after stopping the service's sender loop for that type.
  - A re-send of an already-accepted notification is dropped by MailRelay's key, so the user does not get a duplicate.
  - Known deviation: the monolith does not know how many attempts the service made, so such rows get a fresh attempt count. This is a manual exception, not part of normal rollback.
  - Rows older than 23 h are marked `failed` and paged instead (design rule 6).

## Failure matrix

| Failure | Where it is handled | Result |
|---|---|---|
| Monolith crashes before the enqueuing transaction commits | Row never exists | No notification, as today |
| Monolith crashes after the broker confirms, before `published_at` | Row is re-published | Service dedupes by `id` |
| Broker down | Both outboxes keep their rows | Delayed, not lost; alerts fire |
| Broker redelivers a message | Service `ON CONFLICT (id)` and MailRelay key | One email |
| Service crashes after MailRelay accepts, before commit | Lease expires, re-send with the same key | One email |
| Service crashes after commit, before the result is published | Result outbox republishes | Monolith consumer is idempotent |
| Service crashes after `failed`, before the page | Pager loop reads `paged_at IS NULL` | Page is not lost |
| MailRelay down or timing out | 5 attempts with 1/2/4/8 min backoff | Then `failed` and a page |
| Result message lost | Monolith pending-too-long alert (60 min) | On-call investigates; no automatic resend |
| Flag flip during in-flight work | Route is stored on the row | No row changes owner |
