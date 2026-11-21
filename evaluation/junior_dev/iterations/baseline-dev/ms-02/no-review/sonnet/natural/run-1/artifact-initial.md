# Plan: extract notifications into a separately deployed Notification Service

## Design in brief

**Ownership is a row state, not a flag lookup at send time.** The routing flag only decides which side may claim a new, pending row. Once a row is claimed, only the claimer finishes it. A flag flip, forward or back, therefore cannot make both sides send the same row.

**Monolith `notifications.status` values.** `pending`, `sent` and `failed` are today's values. `publishing` and `handed_off` are new.

| status | meaning | who may touch it |
|---|---|---|
| `pending` | recorded, unclaimed (includes monolith retries waiting on `next_attempt_at`) | old worker, or the relay if the type is routed to the service |
| `publishing` | claimed by the relay, not yet confirmed stored by the broker | relay only (republishes after 60 s without confirmation) |
| `handed_off` | broker confirmed the message is stored | nobody. The service owns delivery from here. |
| `sent`, `failed` | terminal, set by the old worker | nobody |

`handed_off` means "transferred", not "delivered". The delivery outcome lives in the service database.

**Flags.** There is one flag per type: `notifications.route.<type>`, with value `monolith` (default) or `service`. A flag change reaches every monolith instance within 10 s. The relay re-reads the flag each 1 s cycle, and the old worker re-reads it each 5 s poll. A flip is therefore effective in about 15 s, inside the 1-minute requirement.

**Layers of duplicate protection.**
1. The monolith claim is an atomic `SKIP LOCKED` row transition, so each row has one claimer.
2. The service inserts a row keyed by `notification_id` and acks the broker message only after that insert commits. Redelivery then hits a primary-key conflict and is acked without effect.
3. Every MailRelay send passes `idempotency_key = notification id`. This covers a crash between "MailRelay accepted" and "my commit", a timeout where MailRelay actually accepted, and a row handed over after a crash on the other side. MailRelay's dedup window is 24 h, and every crash-recovery path here resolves in minutes. An alert fires on any non-terminal row older than 12 h, so that window is never reached silently.

**Service data.** The service table `notifications(id PK, type, user_id, email, payload, status, attempts, next_attempt_at, created_at_origin, received_at, accepted_at)` is both the dedup inbox and the delivery state. The message carries the full row: `id`, `type`, `user_id`, `email`, `payload`, `attempts`, `next_attempt_at`, `created_at`. The service therefore never needs the monolith's database. There is one broker topic per type (`notifications.<type>`), so a shipping burst cannot queue ahead of `password_reset`.

---

## Steps

### 1. Pass the idempotency key from the old worker (ship alone, first)

- **Starts when:** this is the first step. It needs no other work and no service.
- **Change:** `mailrelay.send(..., idempotency_key=row.id)` in `_deliver`. Nothing else changes.
- **Data / state:** no data moves. State stays in the monolith `notifications` table.
- **Failures:**
  - If an instance dies after MailRelay accepted a batch but before the commit, the rows stay `pending` and are re-sent. MailRelay now drops the repeat and returns success, so the row is marked `sent` with no second email. This removes the roughly 30 duplicates a week.
  - A MailRelay timeout followed by a retry is also safe, because the retries (at most 15 minutes of backoff) fall inside the 24 h window.
- **Exit gate:** duplicate-email reports from support drop to about zero for 1 week. This is a verification of the fix, and it is not a precondition for starting step 2.

### 2. Monolith groundwork, with no behavior change

- **Starts when:** step 1 is deployed.
- **Changes:**
  - An additive migration adds the status values `publishing` and `handed_off`, plus a `handoff_at` column.
  - Flags `notifications.route.{shipping_update,order_confirmed,password_reset}` are created, all set to `monolith`.
  - The worker query gains a type filter: `AND type = ANY(<types whose flag is monolith>)`. It is evaluated per poll.
- **State:** the monolith table and the flags.
- **Failures:**
  - If a flag read fails, the worker treats the type as `monolith`. That is the safe default, because it is today's behavior.
  - Instances still running pre-filter code are harmless. Their worker only reads `pending` rows, and nothing is routed yet.
- **Exit gate:** every monolith instance reports the new version before step 4 enables anything.

### 3. Build and deploy the Notification Service dark

- **Starts when:** it can run in parallel with step 2. It must be finished before step 4 turns on.
- **Components:**
  - **Service database.** Its own database, with the table above. Nothing else reads it.
  - **Consumer.** For each message: (a) insert the row `ON CONFLICT (id) DO NOTHING` with `attempts` and `next_attempt_at` from the message, (b) commit, (c) ack. The ack is last.
  - **Sender.** It polls every 1 s, claims one row at a time with `FOR UPDATE SKIP LOCKED`, and processes `password_reset` first.
    - It renders the template, then calls `send(..., idempotency_key=id)`.
    - It commits per row (not per batch). A crash can still re-send after MailRelay accepts, and the key makes that safe.
  - **Retry policy, identical to today's.** `attempts + 1` is stored on each failure. After failures 1 to 4 the wait is 1, 2, 4, then 8 minutes. After the 5th failure the status becomes `failed`.
  - **Paging.** `alerts.page_oncall` is called before the failing commit, so a crash cannot skip the page. A duplicate page is possible and acceptable.
  - **Template rendering.** A render exception counts as a failed attempt, so it follows the same retry and page path. Today a render exception aborts the whole batch.
  - **Poison messages.** A malformed message is stored as `failed` and paged, then acked.
- **Failures:**
  - **Consumer crashes before the commit.** The message is redelivered after 30 s and processed normally.
  - **Consumer crashes after the commit and before the ack.** The message is redelivered, hits the primary-key conflict, and is acked. No second row is created.
  - **Sender crashes after MailRelay accepted.** The row is still `pending`. Another instance re-sends it, and MailRelay drops the repeat.
  - **MailRelay down.** Attempts burn through the schedule, then the row is `failed` and on-call is paged.
  - **Broker down.** The service receives nothing. The backlog stays in the monolith, and step 4 covers it.
- **Exit gate:** a staging end-to-end test with a fake MailRelay covers each failure above. It includes a message delivered twice, a kill mid-send, and a 5-failure run that ends in `failed` plus a page.

### 4. Add the relay to the monolith (all flags still `monolith`, so it does nothing)

- **Starts when:** step 2 is fully rolled out and the step 3 service is deployed.
- **Relay loop, every 1 s per monolith instance:**
  1. **Claim.** In one transaction, `SELECT ... WHERE status='pending' AND next_attempt_at <= now() AND type = ANY(<types whose flag is service>) ORDER BY created_at LIMIT 100 FOR UPDATE SKIP LOCKED`. Set those rows to `publishing` with `handoff_at = now()`, then commit.
  2. **Publish.** Publish each row's message to its type topic and wait for the broker's storage confirmation.
  3. **Mark.** On confirmation, set the row to `handed_off`.
  4. **Sweep.** Any `publishing` row with `handoff_at` older than 60 s is republished, and `handoff_at` is refreshed. This runs on every instance and uses `SKIP LOCKED`.
- **Data moves:** a message per row from the monolith to the broker. The row stays in the monolith table.
- **State:** monolith table (`publishing` or `handed_off`) plus the broker.
- **Failures:**
  - **Crash after the claim commit and before the publish.** The row sits in `publishing` and the sweep republishes it. Nothing is lost.
  - **Crash after the broker confirm and before the mark.** The sweep republishes the row, and the service dedupes on `id`.
  - **Broker down.** Claimed rows stay `publishing` and retry with backoff. The monolith accepts new notifications as normal (the `enqueue_notification` insert is unchanged). Alerts fire on the age of the oldest `publishing` row and on the `pending` backlog.
  - **Old worker versus relay on the same row.** Only one claim can succeed, because both go through row locks and a status check.
- **Exit gate:** a staging test flips a flag with rows in every state, and each row is sent exactly once.

### 5. Move `shipping_update`

- **Starts when:** steps 1 to 4 are done and checked.
- **Action:** set `notifications.route.shipping_update = service`.
- **Data / state:**
  - New and not-yet-claimed `shipping_update` rows go through the relay to the service.
  - A row the old worker already retried (for example `attempts=2`) is handed over with its `attempts` and `next_attempt_at`, so the 5-attempt budget and the backoff schedule carry over.
  - Rows already `sent` or locked by the old worker finish there. They are never re-claimed.
- **Failures and rollback:**
  - **Rollback.** Set the flag back to `monolith`. The relay stops claiming the type within about 15 s, and the old worker picks up remaining `pending` rows. Rows already `publishing` or `handed_off` stay with the service and finish there. They are not lost and are not re-sent, because the old worker only reads `pending`.
  - **Service or MailRelay down after the cutover.** In-flight rows wait in the broker or in the service table, and are retried or failed per policy. Rollback does not rescue rows already handed off. That is deliberate: pulling them back would create double ownership.
- **Exit gate:** at least 3 days on the service with these conditions:
  - Zero rows older than 12 h that are not terminal.
  - `failed` counts match pages.
  - Service duplicate-conflict counts are explained by redeliveries.
  - Support reports no duplicates.

### 6. Move `order_confirmed`

- **Starts when:** `shipping_update` has run on the service for at least 3 days and its gate is met.
- **Action:** set `notifications.route.order_confirmed = service`. The data, state and failure behavior are as in step 5.
- **Measure:** enqueue-to-MailRelay latency is `accepted_at - created_at_origin` (origin timestamp carried in the message). Both clocks are NTP-synced, and skew is monitored. All `order_confirmed` deliveries are counted, retried ones included.
- **Rollback:** the same flag flip as step 5.
- **Exit gate:** at least 3 days on the service, plus the step 5 conditions, **and p99 enqueue-to-MailRelay latency under 60 s** over the whole run. If p99 is 60 s or more, find and fix the cause, then re-measure for 3 days before step 7. Typical causes are relay or sender poll interval, consumer lag, or a skewed clock.

### 7. Move `password_reset`

- **Starts when:** `order_confirmed` has run on the service for at least 3 days, and the p99 gate from step 6 is met.
- **Action:** set `notifications.route.password_reset = service`. The data, state and failure behavior are as in step 5.
- **Extra watching:**
  - The `password_reset` p99 against the 60 s requirement, with an alert on breach.
  - Topic lag on `notifications.password_reset`.
- **Rollback:** the same flag flip. Rows already handed off stay with the service.
- **Exit gate:** 7 days on the service before step 8. The old worker is kept deployable for the whole 7 days.

### 8. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days with no open incident, and all three types are routed to `service`.
- **Pre-checks:** zero monolith rows are `pending`, and none is stuck in `publishing`.
- **Actions, in order:**
  1. Remove `run_worker` and its startup.
  2. Make the relay claim every type unconditionally.
  3. Remove the route flags.
  4. Keep `enqueue_notification` and the monolith table unchanged. Callers do not change.
- **Failures:**
  - A crash or the broker being down behaves as in step 4.
  - There is no flag rollback after this step. A bad service release is handled by rolling back the service deployment. Handed-off rows stay safe in the service database.

---

## Timeline (earliest possible)

| day | event |
|---|---|
| 0 | step 1 ships; steps 2 to 4 follow |
| about 7 | `shipping_update` moves (step 5) |
| about 10 | `order_confirmed` moves (step 6) |
| about 13 | `password_reset` moves (step 7), if the p99 gate is met |
| about 20 | old worker removed (step 8) |

Dates assume the exit gates pass the first time.
