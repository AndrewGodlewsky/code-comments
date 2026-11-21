# Plan: extract notifications into a Notification Service

## Design in brief

- **Outbox in the monolith.** `enqueue_notification(tx, ...)` and the `notifications` table stay as they are. A new status `handed_off` and a column `handed_off_at` are added. A row's owner is whoever moves it out of `pending` first, under a row lock (`FOR UPDATE SKIP LOCKED`). The old worker moves it to `sent` or `failed`. The new relay moves it to `handed_off`. A row is never reclaimed once `handed_off`.
- **Per-type routing flag.** `notifications.sender.<type>` is `monolith` (default) or `service`. It decides only which component may claim a `pending` row. It never reassigns a row that has already been claimed.
- **The broker carries two topics.**
  - `notification.send` goes from the monolith to the service. Its payload is `id, type, user_id, email, payload, attempts, next_attempt_at, created_at`.
  - `notification.result` goes from the service back to the monolith. It is informational only and never triggers a send.
- **Service state lives in the service DB.** The `notifications` table has `id` as primary key, plus `status`, `attempts`, `next_attempt_at`, `lease_until` and `paged_at`. A `result_outbox` table holds results waiting to be published.
- **Receiving is separate from sending.** The consumer only does "insert if not exists, commit, ack". It never calls MailRelay, so it stays well inside the 30 s ack deadline.
- **Duplicates are prevented at three layers.**
  - The row-ownership rule stops two components from claiming the same row.
  - The service's primary key on `id` stops broker redelivery from creating a second row.
  - MailRelay `idempotency_key = id` covers every crash window around a send. The longest retry horizon is 1+2+4+8 = 15 minutes, which is well inside MailRelay's 24 h window.
- **Retry policy is unchanged.** On failure, attempt n waits `[1,2,4,8][n-1]` minutes. After attempt 5 the row is marked failed and on-call is paged. Timeouts count as failures, as they do today. The service implements this in the same way and carries `attempts` and `next_attempt_at` across the handoff.

## Steps

### 1. Pass the idempotency key on the old worker

- **Starts when:** a normal monolith deploy. This must ship and be verified before any type moves.
- **What moves:** one change in `_deliver`: `mailrelay.send(..., idempotency_key=row.id)`. Nothing else changes.
- **State:** unchanged. It stays in the monolith `notifications` table.
- **Failure handling:**
  - If an instance dies after MailRelay accepts a send but before the batch commits, the rows stay `pending` and are resent with the same key. MailRelay drops the repeat and returns success, so the row ends as `sent`. This fixes today's ~30 duplicates a week.
  - Rows sent before this deploy had no key, so one resend of those is unavoidable.
  - Verify in staging that a repeated key really returns success without a second email.
  - Verify in prod that support's weekly duplicate count drops.
  - If a worker is down for more than 24 hours, a resend falls outside the dedupe window. Alert on `pending` rows older than 1 hour.
- **Exit gate:** deployed everywhere and dedupe confirmed.

### 2. Monolith: type routing flags and a type filter on the old worker (no behavior change)

- **Starts when:** a monolith deploy after step 1. The schema migration is additive, with `handed_off_at` nullable and the new status value allowed.
- **What moves:** three flags `notifications.sender.shipping_update`, `.order_confirmed` and `.password_reset`, all defaulting to `monolith`. The worker's `SELECT` adds `AND type = ANY(<types whose flag is monolith>)`, evaluated inside each batch's transaction.
- **State:** flags live in the flag system. Rows stay in the monolith DB.
- **Failure handling:**
  - With every flag at `monolith`, behavior is identical to step 1, so rolling back this deploy is safe.
  - If the flag read fails, the worker treats the type as `monolith`. Failing closed to the old path avoids stranding rows.
  - A stale flag on one instance for up to 10 s is harmless. It can only make that instance claim a `pending` row that the relay would otherwise have claimed. The row lock decides who gets it, and the key covers any crash window.

### 3. Build and deploy the Notification Service with no traffic

- **Starts when:** the service is deployed with its own DB, its own MailRelay credentials and its own on-call alerting. It has no inbound traffic yet.
- **What moves:** template rendering is copied into the service.
  - A golden-file test renders each of the three types from sample payloads. It asserts the output is byte-identical to the monolith's `templates.render`.
  - Template edits are frozen in both places until decommission.
- **Components:**
  - **Consumer** on `notification.send`: in one service-DB transaction run `INSERT ... ON CONFLICT (id) DO NOTHING`, commit, then ack. Never ack before the commit.
  - **Sender loop** with per-row handling:
    - Claim a due row by setting `lease_until = now()+60s` in a short transaction.
    - Render and call `mailrelay.send(..., idempotency_key=id)` outside any transaction.
    - Record the result in a short transaction: `sent`; or on error set `attempts` and `next_attempt_at` using the exact policy above; or after the 5th failure set `failed` and `paged_at = NULL`.
    - Also enqueue a row in `result_outbox` in the same transaction.
  - **Pager loop:** pages on-call for `failed` rows with `paged_at IS NULL`, then sets `paged_at`.
  - **Result publisher:** publishes `result_outbox` rows, waits for the broker confirm, then marks them published.
  - **Metric:** enqueue-to-MailRelay latency per type, computed as MailRelay accept time minus the message's `created_at`. Note clock skew between systems when reading it.
- **State:** all in the service DB.
- **Failure handling:**
  - **Crash after MailRelay accepts, before the record transaction:** the lease expires and the row is resent with the same key. MailRelay drops it and returns success.
  - **Crash after the row reaches `failed`, before paging:** the pager loop pages from the `paged_at IS NULL` state, so the page is not lost.
  - **Service DB down:** the consumer does not ack, and the broker redelivers when the DB returns.
  - **MailRelay down:** rows retry per policy, then fail and page, as today.
  - **Redelivered message:** the primary key conflict is ignored and the message is acked.
- **Tested in staging.** Kill the process at each point above, redeliver messages, and take down the broker and MailRelay. Assert there are zero duplicate emails and zero lost rows.

### 4. Monolith: handoff relay and result consumer (dormant)

- **Starts when:** a monolith deploy after step 3. All flags are still `monolith`, so the relay finds no rows to claim.
- **What moves:**
  - **Relay** (a background job on the monolith, polling every 1 s):
    - In one transaction, claim `pending` rows whose type flag is `service`, using `FOR UPDATE SKIP LOCKED`.
    - Publish each to `notification.send` with all the fields, including `attempts` and `next_attempt_at`, so the retry state carries over.
    - After the broker confirms storage, set `status='handed_off'` and `handed_off_at=now()`.
  - **Result consumer:** on `notification.result`, run `UPDATE ... SET status=<sent|failed> WHERE id=? AND status='handed_off'`. This is idempotent and informational. It never causes a send.
  - **Reconciler:**
    - For `handed_off` rows with no result after 1 hour, republish the same message and alert.
    - Republishing is safe because the service ignores an id it already has.
    - Page if there is still no result after 24 hours.
- **State:** ownership is recorded in the monolith row (`pending`, then `handed_off`, then `sent` or `failed`). Execution state is in the service DB.
- **Failure handling:**
  - **Broker down:** no confirm arrives, so the row stays `pending`. Checkout is unaffected, because enqueue never touches the broker. Alert when the oldest unhanded `service`-flagged row is older than 30 s. Because the row is still unowned, flipping its flag back to `monolith` lets the old worker send it.
  - **Relay crash after publish, before the status update:** the row is republished on the next pass and the service dedupes by id.
  - **Redelivered result:** the guarded `UPDATE` is a no-op the second time.

### 5. Staging rehearsal of cutover and rollback

- **Starts when:** steps 1–4 are deployed in staging. This is the gate before prod.
- **What moves:** flip each flag to `service` under load, then back, then forward again.
  - Assert that rows already `handed_off` finish in the service after a rollback.
  - Assert that rows still `pending` are sent by the old worker after a rollback.
  - Assert that nothing is sent twice and nothing is lost.
  - Assert that a row with `attempts>0` keeps its `next_attempt_at` through handoff.
  - Assert that flag changes take effect in under 60 s.
- **State:** staging only.
- **Failure handling:** any duplicate or lost row blocks prod. Fix it and repeat.

### 6. Cut over `shipping_update` (40,000/day) in prod

- **Starts when:** steps 1–5 are complete. An operator flips `notifications.sender.shipping_update` to `service`. Within about 10 s every monolith instance has the new value.
- **What moves:** `pending` shipping rows, including any waiting on a retry, are claimed by the relay and sent to the service. Rows already owned by the old worker finish there. The carrier webhook code is unchanged.
- **State:**
  - Monolith DB: `pending`, then `handed_off`, then `sent` or `failed` via the result event.
  - Service DB: the real send state.
- **Failure handling:**
  - Failures follow step 3 (service crash, MailRelay down, redelivery) and step 4 (broker down, relay crash).
  - **Rollback** is flipping the flag back to `monolith`, which takes effect in about 10 s:
    - Unclaimed `pending` rows go to the old worker.
    - `handed_off` rows keep going in the service. Its consumer and sender must stay running until they drain, and the monolith never touches them.
    - The idempotency key covers the one row that could be in both places at once, a row the old worker sent but did not commit before the flip.
- **Hold:** at least 3 days on `service` with these criteria:
  - no duplicates reported
  - no `handed_off` row without a result after an hour
  - no unexpected pages
  - latency metric healthy

### 7. Cut over `order_confirmed` (12,000/day)

- **Starts when:** `shipping_update` has run on the service for at least 3 days and the hold criteria are clean. An operator flips `notifications.sender.order_confirmed` to `service`.
- **What moves, where state lives, failure handling and rollback:** the same as step 6, for this type.
- **Latency gate evidence:** record p99 enqueue-to-MailRelay latency for this type across the hold period, including peak checkout hours. `password_reset` may not move unless it stays under 60 s.
- **Hold:** at least 3 days.

### 8. Cut over `password_reset` (1,500/day, p99 < 60 s)

- **Starts when:** both conditions hold.
  - `order_confirmed` has run on the service for at least 3 days.
  - The service's p99 enqueue-to-MailRelay latency on `order_confirmed` was under 60 s.
  - An operator then flips `notifications.sender.password_reset` to `service`.
- **What moves, where state lives and failure handling:** the same as step 6.
- **Alerts:**
  - Page when this type's p99 over 15 minutes is above 45 s.
  - Page when any password reset row is unhanded or unsent for more than 30 s.
- **Rollback:** the flag flip works as in step 6. For this type, flipping back is the first response to a latency breach. The caveat is the broker-down case from step 4. If the broker is down, unhanded rows are still unowned and the old worker sends them as soon as the flag flips, so no reset waits on the broker.
- **Hold:** 7 days on the service with the old worker still deployable.

### 9. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days, all three flags are `service`, and there are no unresolved latency or duplicate issues. Do this in a separate deploy.
- **What moves:** remove `run_worker`, `_deliver` and the monolith's template rendering and MailRelay credentials. Keep `enqueue_notification` and the relay. Remove the type flags, or leave them fixed at `service`.
- **State:** the monolith `notifications` table stays as the outbox. The service DB holds send state.
- **Failure handling:**
  - Before removing the worker, confirm there are no `pending` rows older than 1 hour and no `handed_off` rows without a result.
  - After the removal, flag-based rollback is no longer available. A rollback is then a redeploy of the previous monolith release.
  - Any service problem is handled by fixing forward. The relay holds unhanded rows, and the service keeps its own state.

## Failure summary

| Situation | Outcome |
|---|---|
| Monolith instance dies mid-send (old worker) | Row stays `pending`, is resent with the same key, and MailRelay drops the repeat |
| Relay dies after publish | Row is republished and the service dedupes by id |
| Broker redelivers a message | Primary key conflict, ignored and acked |
| Service dies after MailRelay accepts | Lease expires and the row is resent with the same key |
| Broker down | Rows stay `pending` and unowned, checkout is unaffected, and a flag flip lets the old worker send them |
| MailRelay down | Retry 1/2/4/8 minutes, then `failed` and on-call paged |
| Flag flipped back with rows in flight | Unclaimed rows go to the old worker, `handed_off` rows finish in the service, and none are lost or resent |
