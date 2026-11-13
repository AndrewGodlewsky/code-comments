# Plan: extract notifications into a Notification Service

## Design in one page

**Ownership.** Exactly one side owns a notification at a time, and the owner is recorded in the monolith row.
- `pending` means the monolith owns it. The old worker sends it, or the relay hands it off.
- `handed_off` means the service owns it. It stays that way until a result event comes back. A `handed_off` row is never sent by the old worker, whatever the flag says.
- `sent` and `failed` are terminal.

**Handoff, with no change for callers.** `enqueue_notification(tx, ...)` still inserts a `pending` row in the caller's transaction. That row is the outbox.
- A new **relay** in the monolith polls `pending` rows of types whose flag says `service`.
- The relay publishes each one to the broker and waits for the publisher confirmation.
- It then marks the row `handed_off` and commits.
- The broker is at-least-once, so the service dedupes on the notification id.

**Return path.** The service publishes a result event (`sent` or `failed`) for each notification. A monolith consumer copies it onto the monolith row. The monolith never reads the service database. A **reconciler** republishes any row that stays `handed_off` with no result for 30 minutes.

**Two layers of duplicate protection.**
1. Service-side dedupe on the id (primary key in the service database).
2. MailRelay `idempotency_key = notification id`, on both the old worker and the service. This covers every crash window where two sides might both send. MailRelay remembers keys for 24 hours. The longest legitimate gap between two sends of the same notification is the 15-minute retry schedule plus crash recovery, so the window is ample.

**Flags.** `notifications.route.<type>` is `monolith` (the default when unset) or `service`. Flag changes reach every monolith instance within 10 s, so rollback fits inside the 1-minute limit. A flag only decides where new `pending` rows go. It never moves a row that is already in flight.

**Messages.**
- `notifications.requested` carries: `schema_version`, `id`, `type`, `user_id`, `email`, `payload`, `created_at`, `attempts`, `next_attempt_at`.
- `notifications.result` carries: `id`, `status` (`sent` or `failed`), `attempts`, `finished_at`.

```
caller tx --> notifications (pending) --relay--> broker --> service DB (insert if new, then ack)
                  ^                                                |
                  |                                     sender: render, MailRelay.send(key=id), retry
                  +-- result consumer <-- broker <-- result publisher <-+
```

---

## Step 1. Pass `idempotency_key` on the old worker

- **Starts when:** this is the first change, a small PR to `app/notifications.py` deployed on its own.
- **Change:** `mailrelay.send(to=..., subject=..., body=..., idempotency_key=row.id)`. The same deploy adds a per-type enqueue-to-MailRelay latency metric (`now() - created_at` at the moment MailRelay accepts) to the old worker. This gives a baseline for the later latency gate.
- **Data moves:** only the key goes to MailRelay. Nothing else changes.
- **State lives:** in the monolith `notifications` table, as before.
- **Failure:**
  - If an instance dies after MailRelay accepted some of a batch but before the commit, the rows stay `pending` and are re-sent. MailRelay now drops the repeat and returns success. This fixes today's roughly 30 duplicates a week.
  - If MailRelay is down, behavior is unchanged: the retry policy applies.
  - Before moving on, confirm in staging that a repeated send with the same key returns success and delivers once.
- **Exit:** deployed. Watch support's duplicate-email reports drop. This is the first fix for the known problem and it protects every later step.

## Step 2. Monolith groundwork: flag-aware worker and the `handed_off` state

- **Starts when:** Step 1 is deployed. Ship as a second, separate deploy.
- **Changes:**
  - Additive migration: add `handed_off_at timestamptz null`, and allow the status value `handed_off` (add it to the enum or check constraint if there is one).
  - The old worker's query additionally excludes types whose `notifications.route.<type>` is `service`. With every flag unset it behaves exactly as today.
- **Data moves:** none.
- **State lives:** monolith database. The flags live in the platform flag system.
- **Failure:**
  - The migration is additive, so rolling the code back is safe.
  - If the flag system is unreachable, the worker treats the type as `monolith` (fail-safe to today's behavior).
- **Exit:** deployed with all flags unset. Behavior is identical to Step 1.

## Step 3. Build and deploy the Notification Service dark

The service has no production traffic yet. It has these components and its own database.

- **Own database.** The table is `svc_notifications(id PK, type, user_id, email, payload, status, attempts, next_attempt_at, created_at, accepted_at, paged bool, result_published bool)`.
- **Consumer.** It reads `notifications.requested`. In one transaction it runs `INSERT ... ON CONFLICT (id) DO NOTHING` and **acks only after that commit**, well inside the 30 s redelivery window. For a duplicate, if the existing row is terminal, it sets `result_published = false` so the result is re-sent.
- **Sender.**
  - It selects due rows `FOR UPDATE SKIP LOCKED`, one row per transaction. It does not use one commit per batch.
  - For each row it renders the template in the service, then calls `mailrelay.send(..., idempotency_key=id)`.
  - Retry policy is identical to today: 5 attempts, waits of 1/2/4/8 minutes before attempts 2 to 5. A failure on attempt 5 sets `status = 'failed', paged = false`.
  - A separate pager step calls `alerts.page_oncall` for rows with `status = 'failed' AND paged = false`, then sets `paged = true`. Paging is at-least-once, so it is never lost on a crash.
- **Result publisher.** It publishes `notifications.result` for terminal rows with `result_published = false`, waits for the confirmation, then sets the flag. A crash causes a republish, and the monolith consumer is idempotent.
- **Templates.** The service ships the three templates. Golden tests render sample payloads for all three types through both the old `templates.render` and the new service renderer and compare the output.
- **Data moves:** none yet. Test only with synthetic messages and staging or sandbox MailRelay. Never send to real users.
- **State lives:** service database only.
- **Failure behavior (tested here with fault injection):**
  - Service crash mid-send: the row is still due, so it is re-sent with the same key. MailRelay drops the repeat.
  - Redelivered message: the insert is a no-op and the message is acked.
  - MailRelay down: retries follow the schedule, then the row is marked `failed` and on-call is paged.
  - Service database down: the consumer cannot ack, so the broker redelivers. Nothing is lost.
  - A unit test compares the retry schedule against the old constants.
- **Exit:** the end-to-end staging suite passes and the service is deployed to production, idle.

## Step 4. Monolith relay, result consumer and reconciler (dark)

- **Starts when:** Step 3 is deployed. Ship as its own deploy, with all flags still `monolith`.
- **Relay.**
  - A thread on each monolith instance (publishing is cheap). Every 1 s it selects `status = 'pending'` rows whose type flag is `service`, `FOR UPDATE SKIP LOCKED`.
  - It publishes `notifications.requested` (including `attempts` and `next_attempt_at`, so a row already waiting out a backoff keeps its schedule) and waits for the broker's confirmation.
  - It then sets `status = 'handed_off', handed_off_at = now()` and commits.
  - A crash after the publish but before the commit causes a republish later. The service dedupes on the id.
- **Result consumer.** It reads `notifications.result` and runs `UPDATE notifications SET status = :s, attempts = :n WHERE id = :id AND status = 'handed_off'`. It acks after the commit, so redelivery is harmless. The monolith does not page, because the service already did.
- **Reconciler.** Every minute it finds rows `handed_off` for more than 30 minutes (the 15-minute retry window plus margin) and republishes them. The service either ignores the message or re-emits the stored result. It also raises an alert on the count of such rows.
- **Data moves:** none yet, because every flag is `monolith`.
- **State lives:** monolith `notifications` table.
- **Failure:**
  - Broker down: the relay cannot publish. Rows stay `pending` and are retried every poll. Nothing is lost, and publish failures do not count as send attempts. An alert fires when the oldest eligible `pending` row is older than 30 s.
  - Result event lost or the consumer is down: the reconciler republishes after 30 minutes.
- **Exit:** staging end-to-end passes, including a drill that kills the relay between publish and commit and checks that exactly one email results.

## Step 5. Move `shipping_update`

- **Starts when:** Step 4 is deployed and verified, and on-call knows the rollback runbook. The trigger is setting `notifications.route.shipping_update = service`.
- **Data moves:**
  - New `shipping_update` rows (about 40,000 a day) are handed off by the relay within about 1 s.
  - Within 10 s the old worker on every instance stops picking up this type.
  - During those 10 s an old-worker instance and a relay instance may both reach the same row. The row lock means only one claims it, and the other skips it.
  - Rows already `pending` with a backoff in progress are handed off with their `attempts` and `next_attempt_at`.
- **State lives:** the row in the monolith (`handed_off`, then `sent` or `failed` via the result event). The sending state is in the service database.
- **Failure:**
  - Crash in the relay: see Step 4.
  - Crash or redelivery in the service: see Step 3.
  - MailRelay down: the service retries, then marks the notification failed and pages. This matches today's behavior.
  - Both sides send the same row: a crashed relay leaves a row `pending` after the service already received it, and a flag flip lets the old worker pick it up. Both calls carry the same key, so MailRelay delivers it once.
- **Rollback drill (during the soak, at a quiet hour):** set the flag back to `monolith`, then to `service` again.
  - Check that new rows were sent by the old worker.
  - Check that rows already `handed_off` were finished by the service and not re-sent.
  - Check that no row was lost.
- **Rollback (any time):** set the flag to `monolith`. The old worker picks up new rows within 10 s. Rows already `handed_off` stay with the service, which keeps running and finishes them. That is why the service and the result consumer must stay deployed. If the service itself is dead and cannot finish them, the reconciler alert fires. An operator can then reset those specific rows to `pending` by hand. This is safe for 24 hours because of the MailRelay key, and it is a manual break-glass step, not an automatic one.
- **Exit:** at least 3 full days on the service, with zero lost rows (the count of `handed_off` rows older than 30 minutes is 0), zero duplicate-email reports, and no unexplained pages. Only then go on to Step 6.

## Step 6. Move `order_confirmed`

- **Starts when:** Step 5's exit criteria are met (at least 3 days). Set `notifications.route.order_confirmed = service`.
- **Data moves, state and failures:** the same as Step 5, for about 12,000 rows a day. The rollback runbook is the same, and the flag is per type.
- **Latency measurement.** The service records `accepted_at - created_at` for every send, using the `created_at` carried in the message (the same clock source as the baseline in Step 1). It reports p50, p95 and p99. The measure includes sends that needed a retry, so a MailRelay problem that pushes more than 1% of sends into a retry will show up in p99.
- **Exit:** at least 3 full days on the service **and** p99 enqueue-to-MailRelay latency under 60 s over that window, including the daily peak. If p99 is not under 60 s, do not move `password_reset`. Find the cause first. Likely causes are the 1 s relay poll, consumer lag, or retries. Then re-measure over a fresh 3 days.

## Step 7. Move `password_reset`

- **Starts when:** Step 6's exit criteria are met, including the latency gate. Set `notifications.route.password_reset = service`.
- **Data moves:** about 1,500 rows a day, following the same path as before. The 60 s requirement continues to apply.
- **Extra safeguards:**
  - An alert fires when the oldest eligible `pending` `password_reset` row is older than 30 s, which would mean the relay or broker is stuck.
  - The same applies to consumer lag.
  - A p99 alert fires at 45 s.
  - If the broker or service is down for more than a short time, the first response is to flip this type back to `monolith`. That takes effect within 10 s, and rows that were already handed off finish on the service.
- **State, failures and rollback:** the same as Step 5.
- **Exit:** 7 full days on the service with zero lost rows, zero duplicates and the latency requirement met. Only then go on to Step 8.

## Step 8. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days and Step 7's exit criteria hold. Until then the old worker stays deployable (Steps 1 to 7 never remove it).
- **Pre-check:** there are no rows `pending` or `handed_off` older than 30 minutes.
- **Changes in the monolith:**
  - Remove `run_worker`, `_deliver` and the retry constants.
  - Remove the monolith copies of the templates (if nothing else uses them).
  - Remove the per-type flags. The relay now hands off every type.
  - Keep `enqueue_notification`, the relay, the result consumer and the reconciler.
- **Data moves:** none new.
- **State lives:** the monolith table is still the first record. The service database owns sending state.
- **Failure and rollback:** after this deploy, going back to monolith sending means redeploying the previous release, not a flag flip. That is accepted at this point, after 7 days of evidence. All other failure behavior stays as in Steps 3 and 4.
- **Exit:** the decommission deploy is live, and a week later the old behavior is gone from the code base.

---

## Failure matrix (any step after 4)

| Event | What happens | Why nothing is lost or doubled |
|---|---|---|
| Monolith crash after the caller's commit | The `pending` row is picked up by the relay or the old worker | The row is the outbox |
| Relay crash between publish and commit | The row is republished later | The service dedupes on the id |
| Broker down | Rows wait as `pending`, with an alert on age | Nothing is dropped; no attempt is consumed |
| Broker redelivers a request | The insert is a no-op and the message is acked | The id is the primary key |
| Service crash after MailRelay accepted | The row is re-sent after restart | The key makes MailRelay drop it |
| MailRelay down | 5 attempts, with waits of 1/2/4/8 minutes, then `failed` and a page | Same policy as today |
| Result event lost | The reconciler republishes after 30 minutes | The service re-emits the stored result |
| Flag flipped back | New rows go to the old worker; in-flight rows finish on the service | Ownership is in the row status, not in the flag |
