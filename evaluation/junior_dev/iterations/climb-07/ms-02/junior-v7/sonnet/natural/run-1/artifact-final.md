# Plan: extract notifications into a Notification Service

## Summary

Today every monolith instance runs a worker thread that reads `pending` rows from the monolith's `notifications` table, renders them, and sends them through MailRelay. It commits once per batch, so a crash after MailRelay accepts some rows but before the commit makes those rows go out again (about 30 duplicate emails a week). Sending also competes with checkout for CPU and database connections.

The new design keeps `enqueue_notification(tx, ...)` and the monolith table as an outbox. A relay hands `pending` rows to a separately deployed Notification Service over the broker. The service owns rendering, sending, retries and paging, and reports the final result back. Types move one at a time behind a flag, so any type can move back by a flag flip. Every send carries the notification id as MailRelay's `idempotency_key`, which is what prevents duplicates.

## Terms

- **Monolith**: the existing application. It has its own database, which holds the `notifications` table.
- **Service**: the new Notification Service. It has its own database, its own MailRelay credentials and its own on-call alerting. The service and the monolith never touch each other's database.
- **Broker**: the message broker already used by billing and search. It is the only channel between monolith and service. It is at-least-once: a message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once a message is stored.
- **MailRelay**: the email provider. `send()` returns success when it accepts a send, and also returns success when it drops a repeat of an `idempotency_key` it accepted in the last 24 h. It raises `mailrelay.Error` on any failure, including a timeout.
- **Old worker**: today's `run_worker` and `_deliver` in the monolith.
- **Relay**: new monolith background job that hands rows to the service.
- **Flag**: a monolith runtime flag read with `flags.get(name)`. A change reaches every monolith instance within 10 s. `notifications.sender.<type>` is `monolith` (default) or `service`, for each of `shipping_update`, `order_confirmed` and `password_reset`. A flag decides only who may claim a `pending` row. It never reassigns a row already claimed.
- **Row lock**: `SELECT ... FOR UPDATE SKIP LOCKED`. The holder owns the row until it commits. Other instances skip locked rows.
- **`attempts` / `next_attempt_at`**: failed sends so far, and the earliest time the next send may run. A row is due when `status='pending'` and `next_attempt_at <= now()`.
- **Lease**: in the service, `lease_until` marks a row as being sent, so other sender passes skip it.

## How it runs

The retry policy is unchanged everywhere: 5 attempts, waits of 1, 2, 4 and 8 minutes before attempts 2 to 5, then the row is marked failed and on-call is paged. Timeouts count as failures. All three types are email only.

1. **Enqueue.** Business code (checkout, carrier webhook, password reset) calls `enqueue_notification(tx, ...)` inside its own transaction. It inserts one `pending` row with a new uuid and returns nothing. The row exists only if that transaction commits, and the caller never touches the broker. State: monolith table. If the transaction rolls back, no row exists, which is correct.

2. **Claim.** Each row has one owner, whoever moves it out of `pending` first under the row lock. If its type's flag is `monolith`, the old worker claims it (its `SELECT` adds `AND type = ANY(<types whose flag is monolith>)`, read inside each batch). If the flag is `service`, the relay claims it. The worker holds the lock during its MailRelay calls until the batch commits. The worker ends rows as `sent` or `failed`. The relay ends its part by setting `handed_off`, and the row is never reclaimed after that. If the flag cannot be read, the worker treats the type as `monolith`, so rows are never stranded. A flag that is stale for up to 10 s on one instance is harmless: the row lock decides the winner and the key covers any crash.

3. **Hand off (relay).** The relay runs on every monolith instance and polls every 1 s. In one transaction it claims `pending` rows of `service` types and publishes each to `notification.send` with `id, type, user_id, email, payload, attempts, next_attempt_at, created_at`. It does not check `next_attempt_at`; the service honors it. After the broker confirms storage it sets `status='handed_off'` and `handed_off_at=now()` and commits. Failure: broker down means no confirm, so the row stays `pending` and unowned. Checkout is unaffected, and flipping the flag back lets the old worker send it. Alert when the oldest unhanded `service`-flagged row is older than 30 s. A relay crash after publish but before commit leaves the row `pending`; the next pass republishes it and the service ignores the repeat id.

4. **Receive (service consumer).** On `notification.send`, in one service-DB transaction: `INSERT ... ON CONFLICT (id) DO NOTHING`, commit, then ack. It never acks before the commit and never calls MailRelay, so it stays inside the 30 s ack deadline. It stores `attempts` and `next_attempt_at` as given, even if in the future. If the id already exists and that row is `sent` or `failed`, the same transaction also adds a fresh `result_outbox` row, so a lost result reaches the monolith again. State: service `notifications` table (`id` primary key, `status` of `pending`, `sent` or `failed`, `attempts`, `next_attempt_at`, `lease_until`, `paged_at`) and a `result_outbox` table. Failure: if the service DB is down, it does not ack and the broker redelivers. A redelivered message hits the primary key, is ignored and is acked.

5. **Send (service sender loop).** It polls every 1 s. A row is due when `status='pending'`, `next_attempt_at <= now()` and `lease_until` is null or past. So a handed-off row whose time has passed is sent on the next poll, and a future one waits.
   - Claim: set `lease_until = now()+60s` in a short transaction.
   - Render and call `mailrelay.send(..., idempotency_key=id)` outside any transaction.
   - Record in a short transaction: `sent`; or on error set `attempts` and `next_attempt_at` per the policy; or after the 5th failure set `failed` and `paged_at = NULL`.
   - Only when the row becomes `sent` or `failed`, add a `result_outbox` row in that same transaction. A row waiting on a retry writes no result, so the monolith sees it as `handed_off` until it is final.
   - Failure: a crash after MailRelay accepts but before recording lets the lease expire; the row is resent with the same key and MailRelay drops it and returns success. MailRelay down means retries per policy, then `failed` and a page.

6. **Page (service pager loop).** It pages on-call for `failed` rows with `paged_at IS NULL`, then sets `paged_at`. A crash between failing and paging loses nothing. The service is the only component that pages on failure; the monolith's result consumer never pages.

7. **Report back (result publisher and result consumer).** The publisher sends `result_outbox` rows to `notification.result` (carrying `id` and `sent` or `failed`), waits for the broker confirm, then marks them published. If the broker is down, or it crashes before marking, the row is published again. The monolith's result consumer runs `UPDATE ... SET status=<sent|failed> WHERE id=? AND status='handed_off'`, so repeats do nothing. Results are informational: they never cause a send. They let the monolith table show the outcome and let the reconciler see which rows are finished.
   - **Result before relay commit:** the service can finish before the relay commits. The `UPDATE` waits on the relay's row lock, then sees `handed_off` and applies. If the relay rolled back instead, the row is `pending`, the `UPDATE` matches nothing and the result is dropped. The relay republishes on its next pass, the service's consumer queues the result again (step 4), and it applies.

8. **Reconcile (monolith).** For `handed_off` rows with no result after 1 hour, republish the same message and alert. This is safe: the service never creates a second row for an id, and if it already finished that row, step 4 queues the result again so the row leaves `handed_off`. If it has not finished, nothing changes. Page if there is still no result after 24 hours.

**Why no duplicates:** the row lock stops two components claiming one row; the service primary key stops broker redelivery making a second row; the MailRelay key covers every crash around a send. The longest retry horizon is 1+2+4+8 = 15 minutes, well inside MailRelay's 24 h window.

**Metric:** enqueue-to-MailRelay latency per type, as MailRelay accept time minus the message's `created_at`. Clock skew between systems affects it.

### Failure summary

| Situation | Outcome |
|---|---|
| Monolith instance dies mid-send (old worker) | Row stays `pending`, is resent with the same key, MailRelay drops the repeat |
| Relay dies after publish | Row is republished, the service dedupes by id |
| Broker redelivers a message | Primary key conflict, ignored and acked |
| Service dies after MailRelay accepts | Lease expires, row is resent with the same key |
| Result lost or published twice | Reconciler republishes the send, service re-queues the result, guarded update ignores repeats |
| Result arrives before relay commits | Update waits for the lock and applies; if the relay rolls back, the republish re-queues the result |
| Broker down | Rows stay `pending` and unowned, checkout unaffected, a flag flip lets the old worker send them |
| MailRelay down | Retry 1/2/4/8 minutes, then `failed` and on-call paged by the service |
| Flag flipped back with rows in flight | Unclaimed rows go to the old worker, `handed_off` rows finish in the service, none lost or resent |

## Rollout, in order

### 1. Pass the idempotency key on the old worker
- **Starts:** a normal monolith deploy. It must ship and be verified before any type moves.
- **Change:** in `_deliver`, `mailrelay.send(..., idempotency_key=row.id)`. Nothing else. State stays in the monolith table.
- **Failure handling:** if an instance dies after MailRelay accepts but before the commit, rows are resent with the same key, MailRelay drops the repeat, and the row ends `sent`. This fixes the ~30 duplicates a week. Rows sent before the deploy had no key, so one resend of those is unavoidable. If a worker is down for more than 24 hours, a resend falls outside the dedupe window, so alert on `pending` rows older than 1 hour.
- **Exit gate:** deployed everywhere. Confirm in staging that a repeated key returns success without a second email, and in prod that support's weekly duplicate count drops.

### 2. Monolith: flags and type filter (no behavior change)
- **Starts:** a monolith deploy after step 1, with an additive migration: nullable `handed_off_at` and the new `handed_off` status value.
- **Change:** add the three flags, all `monolith`, and the type filter on the worker's `SELECT`. Flags live in the flag system, rows stay in the monolith DB.
- **Failure handling:** with every flag at `monolith`, behavior equals step 1, so rolling back this deploy is safe.

### 3. Build and deploy the Notification Service with no traffic
- **Starts:** the service is deployed with its DB, MailRelay credentials and alerting, and no inbound traffic.
- **Change:** build the consumer, sender loop, pager loop, result publisher and metric described above. Copy template rendering into the service. A golden-file test renders each of the three types from sample payloads and asserts output is byte-identical to the monolith's `templates.render`. Freeze template edits in both places until decommission. State is all in the service DB.
- **Staging test:** kill the process at each failure point above, redeliver messages, and take down the broker and MailRelay. Assert zero duplicate emails and zero lost rows.

### 4. Monolith: relay, result consumer and reconciler (dormant)
- **Starts:** a monolith deploy after step 3. All flags are still `monolith`, so the relay finds nothing to claim.
- **Change:** add the relay, result consumer and reconciler described above.

### 5. Staging rehearsal of cutover and rollback
- **Starts:** steps 1 to 4 are deployed in staging. This is the gate before prod.
- **Do:** flip each flag to `service` under load, back, then forward again. Assert that `handed_off` rows finish in the service after a rollback, `pending` rows are sent by the old worker after a rollback, nothing is sent twice or lost, a row with `attempts>0` keeps its `next_attempt_at` through handoff, and flag changes take effect in under 60 s.
- **Failure handling:** any duplicate or lost row blocks prod. Fix it and repeat.

### 6. Cut over `shipping_update` (40,000/day) in prod
- **Starts:** steps 1 to 5 are complete. An operator flips `notifications.sender.shipping_update` to `service`. Within about 10 s every monolith instance sees it.
- **Effect:** `pending` shipping rows, including those waiting on a retry, are claimed by the relay. Rows already owned by the old worker finish there. Carrier webhook code is unchanged. Monolith DB holds `pending`, `handed_off`, then `sent` or `failed`; the service DB holds the real send state.
- **Rollback:** flip the flag back to `monolith`; it takes effect in about 10 s, within the one-minute requirement. Unclaimed `pending` rows go to the old worker. `handed_off` rows keep going in the service, whose consumer and sender must stay running until they drain; the monolith never touches them. The key covers the one row that could be in both places: one the old worker sent but did not commit before the flip. Rollback loses and re-sends nothing in flight.
- **Hold:** at least 3 days on `service`, with no duplicates reported, no `handed_off` row without a result after an hour, no unexpected pages, and a healthy latency metric.

### 7. Cut over `order_confirmed` (12,000/day)
- **Starts:** `shipping_update` has run on the service for at least 3 days and the hold criteria are clean. An operator flips `notifications.sender.order_confirmed` to `service`.
- **Effect, state, failures, rollback:** as step 6.
- **Latency evidence:** record p99 enqueue-to-MailRelay latency for this type across the hold, including peak checkout hours. `password_reset` may not move unless this stays under 60 s.
- **Hold:** at least 3 days.

### 8. Cut over `password_reset` (1,500/day, p99 under 60 s)
- **Starts:** `order_confirmed` has run on the service for at least 3 days and its p99 enqueue-to-MailRelay latency was under 60 s. An operator then flips `notifications.sender.password_reset` to `service`.
- **Effect, state, failures:** as step 6.
- **Alerts:** page when this type's p99 over 15 minutes is above 45 s, and when any password reset row is unhanded or unsent for more than 30 s.
- **Rollback:** as step 6. Flipping back is the first response to a latency breach. If the broker is down, unhanded rows are still unowned and the old worker sends them as soon as the flag flips, so no reset waits on the broker.
- **Hold:** 7 days on the service with the old worker still deployable.

### 9. Decommission the old worker
- **Starts:** `password_reset` has run on the service for 7 days, all three flags are `service`, and no latency or duplicate issues are unresolved. Do it in a separate deploy.
- **Before removing:** confirm no `pending` rows older than 1 hour and no `handed_off` rows without a result.
- **Change:** remove `run_worker`, `_deliver`, the monolith's template rendering and its MailRelay credentials. Keep `enqueue_notification` and the relay. Remove the type flags or leave them fixed at `service`. The monolith table stays as the outbox; the service DB holds send state.
- **Failure handling:** flag-based rollback is no longer available. Rollback is a redeploy of the previous monolith release. Service problems are fixed forward: the relay holds unhanded rows and the service keeps its own state.

## Open questions

- MailRelay's call timeout is not documented in the files. The 60 s lease must be longer than it, or a slow call could be resent while in flight (the key would still prevent a duplicate email). Confirm the timeout.
- How an operator edits a flag (tool or UI) is not described in the files.
- Whether anyone, such as support, reads the monolith row's final `sent`/`failed` status is not known.
- The relay-commit race in step 7 of "How it runs" relies on the monolith database making an `UPDATE` wait for a row lock and re-check its `WHERE` (as PostgreSQL does). The files do not name the database; confirm this.
