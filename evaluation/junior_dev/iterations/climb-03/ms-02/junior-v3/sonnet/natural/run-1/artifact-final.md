# Plan: extract notifications into a Notification Service

## What this is

Callers keep inserting a `pending` row into the monolith `notifications` table, inside their own transaction. That row is the outbox. For each type whose flag says `service`, a relay in the monolith publishes the row to the broker. A separately deployed Notification Service stores it in its own database, renders the template, sends it through MailRelay, and publishes a result event back. The monolith copies the result onto its row. Types move one at a time (`shipping_update`, then `order_confirmed`, then `password_reset`), and each move can be undone by flipping a flag.

## Terms

- **Broker:** the existing at-least-once message broker (billing and search use it). A *publisher confirmation* means the broker has stored the message. A message not acked within 30 s is redelivered, possibly to another consumer.
- **MailRelay:** the email service. `send()` success means it accepted the send. If it already accepted the same `idempotency_key` in the last 24 hours, it drops the new send and also returns success.
- **Flag:** `notifications.route.<type>`, read with `flags.get`. Its value is `monolith` (default when unset) or `service`. A change reaches every monolith instance within 10 s. A flag only decides where new `pending` rows go. It never moves a row already in flight.
- **Owner:** the monolith row status says who owns a notification.
  - `pending`: the monolith owns it. The old worker sends it, or the relay hands it off.
  - `handed_off`: the service owns it until a result event comes back. The old worker never sends a `handed_off` row, whatever the flag says.
  - `sent` and `failed`: terminal.
- **Relay:** a new monolith thread that publishes `pending` rows of `service` types to the broker.
- **Reconciler:** a new monolith job that republishes rows stuck in `handed_off`.
- **Two layers against duplicates:** (1) the service dedupes on the notification id (its primary key); (2) every send, from the old worker or the service, passes the notification id as the MailRelay `idempotency_key`. The 24-hour key memory far exceeds the longest legitimate gap between two sends of one notification (the 15-minute retry schedule plus crash recovery).
- **Retry policy (unchanged):** 5 attempts, waits of 1/2/4/8 minutes before attempts 2 to 5, then mark `failed` and page on-call.

Messages:
- `notifications.requested`: `schema_version`, `id`, `type`, `user_id`, `email`, `payload`, `created_at`, `attempts`, `next_attempt_at`.
- `notifications.result`: `id`, `status` (`sent` or `failed`), `attempts`, `finished_at`.

```
caller tx --> notifications (pending) --relay--> broker --> service DB (insert if new, then ack)
                  ^                                                |
                  |                                     sender: render, MailRelay.send(key=id), retry
                  +-- result consumer <-- broker <-- result publisher <-+
```

## Steps

### 1. Pass `idempotency_key` on the old worker

- **Starts when:** this is the first change, a small PR to `app/notifications.py`, deployed on its own.
- **Change:** `mailrelay.send(..., idempotency_key=row.id)`. The same deploy adds a per-type enqueue-to-MailRelay latency metric (`now() - created_at` when MailRelay accepts). This is the baseline for the later latency gate.
- **Data moves / state:** only the key goes to MailRelay. State stays in the monolith table.
- **If something fails:** if an instance dies after MailRelay accepted part of a batch but before the commit, the rows are re-sent and MailRelay now drops the repeat. That fixes today's roughly 30 duplicates a week. If MailRelay is down, the retry policy applies as before.
- **Before moving on:** confirm in staging that a repeated send with the same key returns success and delivers once.

### 2. Monolith groundwork: flag-aware worker and `handed_off`

- **Starts when:** step 1 is deployed. Ship as a separate deploy.
- **Change:** an additive migration adds `handed_off_at timestamptz null` and allows the status `handed_off`. The old worker's query also skips types whose flag is `service`. With every flag unset it behaves exactly as today.
- **Data moves:** none. State is in the monolith database; flags are in the flag system.
- **If something fails:** the migration is additive, so rolling code back is safe. If the flag system is unreachable, the worker treats the type as `monolith`.

### 3. Build and deploy the Notification Service dark

The service has its own database and no production traffic yet.

- **Table** `svc_notifications(id PK, type, user_id, email, payload, status, attempts, next_attempt_at, created_at, accepted_at, paged bool, result_published bool)`. `status` is `pending`, `sent` or `failed`.
- **Consumer:** reads `notifications.requested`. In one transaction it runs `INSERT ... ON CONFLICT (id) DO NOTHING` and acks only after the commit.
  - A new id is stored as `pending`, taking `attempts` and `next_attempt_at` from the message (only this once), so a row already waiting out a backoff keeps its schedule.
  - A known `pending` id is ignored; the sender's schedule wins.
  - A known terminal id gets `result_published = false`, so its result is re-sent.
- **Sender:** every few seconds, it selects due rows (`status = 'pending' AND next_attempt_at <= now()`) with `FOR UPDATE SKIP LOCKED`, one row per transaction. For each row it renders the template, then calls `mailrelay.send(..., idempotency_key=id)`.
  - Success: `status = 'sent'`, `attempts + 1`, set `accepted_at`.
  - MailRelay error: `attempts + 1` and set `next_attempt_at` by the retry policy. A failure on attempt 5 sets `status = 'failed', paged = false`.
- **Pager:** for rows with `status = 'failed' AND paged = false`, it calls `alerts.page_oncall`, then sets `paged = true`. Paging is at-least-once, so a crash never loses a page.
- **Result publisher:** publishes `notifications.result` for terminal rows with `result_published = false`, waits for confirmation, then sets the flag. A crash causes a republish.
- **Templates:** the service ships all three. Golden tests render sample payloads through the old `templates.render` and the new renderer and compare.
- **Data moves:** none yet. Use synthetic messages and sandbox MailRelay only, never real users. State is in the service database only.
- **If something fails (tested with fault injection):**
  - Service crash mid-send: the row is still due and is re-sent with the same key; MailRelay drops the repeat.
  - Redelivered message: the insert is a no-op and the message is acked.
  - MailRelay down: retries follow the schedule, then `failed` and a page.
  - Service database down: the consumer cannot ack, the broker redelivers, nothing is lost.
  - A unit test compares the retry schedule to the old constants.
- **Exit:** the staging end-to-end suite passes and the service is deployed to production, idle.

### 4. Monolith relay, result consumer and reconciler (dark)

- **Starts when:** step 3 is deployed. Ship as its own deploy, all flags still `monolith`.
- **Relay:** a thread on each monolith instance. Every 1 s it reads each type's flag and selects `pending` rows of `service` types, `FOR UPDATE SKIP LOCKED`, up to a fixed batch. It publishes `notifications.requested` (with `attempts` and `next_attempt_at`), waits for the confirmation, then sets `status = 'handed_off', handed_off_at = now()` and commits.
- **Result consumer:** reads `notifications.result` and runs `UPDATE notifications SET status = :s, attempts = :n WHERE id = :id AND status = 'handed_off'`, then acks after the commit. Redelivery is harmless. The monolith does not page, because the service already did.
- **Reconciler:** every minute it republishes rows that have been `handed_off` for more than 30 minutes (the 15-minute retry window plus margin) and raises an alert on their count. The service then handles each by id: unseen, it inserts and sends; still retrying, it ignores; terminal, it re-emits the stored result.
- **Data moves:** none yet. State is in the monolith table.
- **If something fails:**
  - Relay crash between publish and commit: the row is republished later; the service dedupes on the id.
  - Broker down: rows stay `pending` and are retried every poll. Publish failures do not consume send attempts. An alert fires when the oldest eligible `pending` row is older than 30 s, and the response is to flip the flag back to `monolith`.
  - Result event lost or consumer down: the reconciler republishes after 30 minutes.
- **Exit:** staging end-to-end passes, including a drill that kills the relay between publish and commit and checks that exactly one email results.

### 5. Move `shipping_update`

- **Starts when:** step 4 is deployed and verified, and on-call knows the rollback runbook. Set `notifications.route.shipping_update = service`.
- **Data moves:** new rows (about 40,000 a day) are handed off by the relay within about 1 s. Within 10 s every old worker stops picking up this type. During those 10 s an old worker and a relay may reach the same row; the row lock lets only one claim it. Rows already `pending` mid-backoff are handed off with their `attempts` and `next_attempt_at`.
- **State lives:** the monolith row (`handed_off`, then `sent` or `failed` via the result event); sending state is in the service database.
- **If something fails:**
  - Relay crash: the row is republished and deduped.
  - Service crash or redelivery: re-sent with the same key, or ignored as a duplicate.
  - MailRelay down: the service retries, then marks `failed` and pages, as today.
  - Both sides send the same row (a crashed relay leaves a row `pending` after the service received it, then a flag flip lets the old worker take it): both calls carry the same key, so MailRelay delivers once.
- **Rollback drill (during the soak, at a quiet hour):** set the flag to `monolith`, then back to `service`. Check that new rows were sent by the old worker, that `handed_off` rows were finished by the service and not re-sent, and that none were lost.
- **Rollback (any time):** set the flag to `monolith`. The old worker takes new rows within 10 s. Rows already `handed_off` stay with the service, which keeps running and finishes them, so the service and result consumer must stay deployed. If the service itself is dead, the reconciler alert fires, and an operator may reset those specific rows to `pending` by hand. This is a manual break-glass step, safe for 24 hours because of the MailRelay key.
- **Exit:** at least 3 full days on the service with zero `handed_off` rows older than 30 minutes, zero duplicate-email reports and no unexplained pages.

### 6. Move `order_confirmed`

- **Starts when:** step 5's exit is met. Set `notifications.route.order_confirmed = service`.
- **Data, state, failures, rollback:** as in step 5, for about 12,000 rows a day. The flag is per type.
- **Latency measurement:** the service records `accepted_at - created_at` for every send, using `created_at` from the message (same clock source as step 1's baseline), and reports p50, p95 and p99. Sends that needed a retry are included.
- **Exit:** at least 3 full days on the service and p99 enqueue-to-MailRelay under 60 s over that window, including the daily peak. If not, do not move `password_reset`. Find the cause (likely the 1 s relay poll, consumer lag or retries), then re-measure over a fresh 3 days.

### 7. Move `password_reset`

- **Starts when:** step 6's exit is met, including the latency gate. Set `notifications.route.password_reset = service`.
- **Data, state, failures, rollback:** as in step 5, for about 1,500 rows a day. The 60 s p99 requirement continues to apply.
- **Extra safeguards:** alerts fire when the oldest eligible `pending` `password_reset` row is older than 30 s, when consumer lag grows, and when p99 reaches 45 s. If the broker or service is down for more than a short time, flip this type back to `monolith`; that takes effect within 10 s and rows already handed off finish on the service.
- **Exit:** 7 full days on the service with zero lost rows, zero duplicates and the latency requirement met.

### 8. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days. Until then the old worker stays deployable.
- **Pre-check:** no rows `pending` or `handed_off` older than 30 minutes.
- **Change in the monolith:** remove `run_worker`, `_deliver`, the retry constants, the monolith template copies (if unused elsewhere) and the per-type flags (the relay now hands off every type). Keep `enqueue_notification`, the relay, the result consumer and the reconciler.
- **State lives:** the monolith table is still the first record; the service database owns sending state.
- **If something fails / rollback:** going back to monolith sending now means redeploying the previous release, not a flag flip. This is accepted after 7 days of evidence. All other failure handling is unchanged.

## What happens when things fail

| Event | What happens | Why nothing is lost or doubled |
|---|---|---|
| Monolith crash after the caller's commit | The `pending` row is picked up by the relay or old worker | The row is the outbox |
| Relay crash between publish and commit | The row is republished later | The service dedupes on the id |
| Broker down | Rows wait as `pending`, with an age alert | Nothing dropped; no attempt consumed |
| Broker redelivers a request | The insert is a no-op and the message is acked | The id is the primary key |
| Service crash after MailRelay accepted | The row is re-sent after restart | The key makes MailRelay drop it |
| MailRelay down | 5 attempts at 1/2/4/8 minute waits, then `failed` and a page | Same policy as today |
| Result event lost | The reconciler republishes after 30 minutes | The service re-emits the stored result |
| Flag flipped back | New rows go to the old worker; in-flight rows finish on the service | Ownership is in the row status, not the flag |

## Open questions

- Who may change the `notifications.route.<type>` flags, and whether MailRelay delivers to the user synchronously with accepting a send, are not stated in the source files. The plan does not depend on either.
