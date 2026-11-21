# Plan: extract notifications into a Notification Service

## Summary

Today, a background worker inside the monolith reads `pending` rows from the `notifications` table, renders the email, and sends it through MailRelay (the email provider). We will move that work into a separate Notification Service, one notification type at a time, without losing or duplicating any email.

The monolith keeps recording every notification in its own table. A new monolith job (the relay) hands rows to the service over the message broker. The service renders and sends the email, then reports the result back over the broker.

Terms used below:
- **Broker:** the existing message broker. It delivers at least once. If a message is not acknowledged ("acked") within 30 s, it is redelivered, possibly to a different consumer. A publisher gets a confirmation once the broker has stored a message.
- **Flag:** a runtime flag read with `flags.get(name)`. A change reaches every monolith instance within 10 s.
- **Idempotency key:** MailRelay's `send()` accepts an optional `idempotency_key`. If it has already accepted a send with the same key in the last 24 h, it drops the new one and returns success.
- **`SKIP LOCKED`:** `SELECT ... FOR UPDATE SKIP LOCKED` locks the rows it selects and silently skips rows another transaction has already locked. Two workers using it never take the same row.

## How the design works

**Ownership.** At any moment, each row in the monolith `notifications` table has exactly one owner: the monolith (old worker) or the service. Ownership changes only through an atomic status change on the row (a database update that either happens fully or not at all). It never changes because a flag changed. This one rule prevents lost and duplicate emails.

```
Monolith owns the row:
  pending --(old worker locks the row and sends)--> sent | failed

Service owns the row:
  pending --(relay claims the row)--> publishing --(broker confirms)--> published
  published --(result event from service)--> sent | failed   (monolith copy, informational only)
```

`publishing` means "claimed by the relay, not yet confirmed stored by the broker". `published` means "the broker has stored it; the service now owns the work".

**Components.**
- **Old worker.** Today's `run_worker` in the monolith. It sends mail itself and selects only `pending` rows.
- **Relay.** A new monolith background job. It claims `pending` rows of types routed to the service and publishes them to the broker topic `notifications.send`.
- **Notification Service.** A separately deployed service with its own database. It receives messages, renders templates, calls MailRelay, and publishes results to the topic `notifications.result`. It never connects to the monolith database, and the monolith never connects to its database.
- **Result consumer.** A new monolith job that copies the service's `sent`/`failed` results onto the monolith row.
- **Routing flags.** `notifications.route.<type>` is `monolith` (default) or `service`. It decides who claims rows that are still `pending`.

**Rules that make this safe.**
- **Handoff is one-way.** Once the relay moves a row to `publishing`, the old worker never touches it again.
- **The flag routes `pending` rows only.** It never moves a row back.
- **Rollback is safe.** Flipping a flag back to `monolith` cannot cause a double send. Rows already handed over finish in the service, which keeps running for every type regardless of the flag.
- **Flag skew is safe.** Monolith instances can disagree about a flag for up to 10 s. Both the relay and the old worker claim rows with `SKIP LOCKED` plus a status check, so only one of them can take a given row.
- **Three layers of duplicate protection.**
  1. Single ownership per row.
  2. The service dedups inbound messages by notification id (its primary key).
  3. Every send passes `idempotency_key = notification id`. MailRelay drops repeats for 24 h, and the longest retry chain is 1+2+4+8 = 15 min.
- **Handoff message contents.** `id, type, user_id, email, payload, created_at, attempts, retry_after_seconds`. The relay claims any `pending` row of a routed type, including one that is waiting out a retry delay. That row keeps its attempt count, so the 5-attempt policy stays exact across a handoff. `retry_after_seconds` is the remaining delay as a relative number, so clock differences between systems do not matter.
- **Same retry policy on both sides.** `MAX_ATTEMPTS = 5` and `BACKOFF_MINUTES = [1, 2, 4, 8]`. A shared test table asserts the two implementations match.
- **A bug in today's worker.** In `_deliver`, `templates.render` runs outside the `try`. A render exception rolls back the whole batch, and the same rows are picked up again forever. The service avoids this by rendering inside the retry handling, so a render error counts as a failed attempt. The old worker is left as is, because it is being removed; step 1 adds only the idempotency key to it.

---

## Steps

Steps are in shipping order. Step 3 can be built in parallel with steps 1 and 2.

### 1. Pass the idempotency key from the old worker (ships alone, first)

- **Starts when:** immediately. It needs no other step and is the prerequisite for everything else.
- **What moves:** one change in `_deliver`: `mailrelay.send(..., idempotency_key=row.id)`. No schema or flag changes.
- **State lives in:** the monolith `notifications` table, as today. MailRelay holds the 24 h key memory.
- **If something fails:**
  - **An instance dies after MailRelay accepted part of a batch but before the commit.** Those rows stay `pending` and are sent again, as today. MailRelay now drops the repeat and returns success, so the row is marked `sent` with no second email. This should remove the roughly 30 duplicates a week.
  - **MailRelay times out but actually accepted the send.** The retry reuses the key, so it is dropped.
  - **MailRelay is down.** Behavior is unchanged. After 5 attempts the row is marked `failed` and on-call is paged.
- **Exit check:** the weekly duplicate-email count from Support falls to about zero. Keep watching it, because it is the baseline for every later step.

### 2. Monolith groundwork: statuses, routing flags, filtered worker (additive; all types still on the monolith)

- **Starts when:** step 1 is deployed everywhere.
- **What moves:**
  - An additive migration adds the statuses `publishing` and `published`, plus nullable `published_at` and `lease_until` columns. Existing rows and code are unaffected.
  - Three flags, `notifications.route.shipping_update`, `.order_confirmed` and `.password_reset`, all defaulting to `monolith`.
  - The worker query gains `AND type = ANY(<types currently routed to monolith>)`. It reads the flags once per poll.
  - `enqueue_notification` is unchanged, so callers do not change.
- **State lives in:** the monolith DB for rows, and `flags.get` for routing.
- **If something fails:**
  - **A rolling deploy runs old and new code side by side.** All flags are `monolith`, so both versions do the same thing.
  - **The flag read fails.** The worker treats every type as `monolith`, which is today's behavior.
- **Gate:** do not move on until 100% of instances run this version, and set no flag to `service` before then. The filter must be on every instance first, so that an old-code instance cannot send rows the service has been told to own.

### 3. Build the Notification Service (own deployment, own database, staging only)

- **Starts when:** any time. It can run in parallel with steps 1 and 2, and nothing in production depends on it yet.
- **What moves:** messages arrive from the broker, are stored in the service's database, are sent to MailRelay, and results go back out through the broker.
- **State lives in:** the service's own database.
  - `inbox_notifications`, primary key `id`. Columns: `type, user_id, email, payload, created_at, attempts, next_attempt_at, status (pending|sent|failed), accepted_at, page_pending`.
  - `result_outbox`: `sent`/`failed` events waiting to be published.
  - `page_pending` is a flag on a failed row. It stays set until on-call has been paged.
- **Parts:**
  - **Consumer.** It subscribes to `notifications.send`. In one transaction it runs `INSERT ... ON CONFLICT (id) DO NOTHING`, then acks. It never calls MailRelay, so it always acks well inside the broker's 30 s redelivery window. The first send attempt is triggered right after the insert instead of waiting for a poll, to keep latency low.
  - **Sender.** For each row, in its own transaction:
    1. Select with `FOR UPDATE SKIP LOCKED` where `status='pending' AND next_attempt_at <= now()`.
    2. Render the template (now owned by the service) and call `mailrelay.send(..., idempotency_key=id)`, both inside the same `try`.
    3. On success, set `sent` and `accepted_at` and write a `result_outbox` row, all in that transaction.
    4. On error, apply the old policy. Below 5 attempts, schedule a retry with backoff of 1/2/4/8 minutes. On the fifth failure, mark the row `failed`, write a result event and set `page_pending`.
    5. After the commit of a failure, call `alerts.page_oncall` and clear `page_pending`. A sweeper re-pages any row still marked `page_pending`.
  - **Result publisher.** It publishes `result_outbox` rows to `notifications.result`, deletes each row after the broker confirms it, and republishes unconfirmed rows.
  - **Retention.** Inbox rows are kept for 30 days, longer than any plausible redelivery or replay window.
  - **Tests.** Golden-file tests compare the service's rendered subject and body with the monolith's `templates.render` output for recorded payloads of all three types. A table-driven test asserts that the attempt and backoff sequence matches the old worker.
- **If something fails:**
  - **The service dies after the MailRelay call but before the commit.** The row is still `pending`, so it is retried. MailRelay drops the repeat via the key, because the retry is minutes away, well inside 24 h.
  - **The service dies after the insert but before the ack.** The broker redelivers, possibly to another consumer. The primary-key conflict makes it a no-op.
  - **MailRelay is down.** The retry policy applies and the attempt counter advances exactly as today.
  - **The broker is down.** The service cannot receive new work or publish results. Rows already received keep sending. Results queue in `result_outbox` and flow when the broker returns.
  - **Residual risk.** If the service is down for more than 24 h after MailRelay accepted a send but before the commit, the later resend falls outside the dedup window and could duplicate. To keep outages far from 24 h, page on-call when the oldest `pending` row is older than 1 hour.

### 4. Monolith relay and result consumer (deployed dark: no type routed yet)

- **Starts when:** steps 2 and 3 are done.
- **What moves:**
  - **Relay.** It runs every 1 s and covers only types whose flag is `service`.
    - *Phase A, claim.* In one short transaction, pick a batch of `pending` rows with `SKIP LOCKED` (this skips any row the old worker has locked), set `status='publishing', lease_until=now()+30s`, and commit. The lease is a deadline: if the row is still `publishing` after it, the relay is presumed to have crashed.
    - *Phase B, publish.* Publish each claimed row to `notifications.send` and wait for the broker's confirmation.
    - *Phase C, record.* For confirmed rows, set `status='published', published_at=now()`.
  - **Recovery sweep.** Rows stuck in `publishing` past `lease_until` are republished. Duplicates are harmless because the service dedups by id. This is how a relay crash between claiming and publishing loses nothing.
  - **Broker outage.** After a failed publish, the relay stops claiming new batches until a publish succeeds. At most one batch is therefore stranded in `publishing` during an outage.
  - **Result consumer.** It reads `notifications.result` and runs `UPDATE notifications SET status = <sent|failed> WHERE id = %s AND status IN ('published','publishing')`. It is idempotent, so redelivery is harmless.
  - **Watchdog alert.** Any row that stays in `published` or `publishing` for more than 30 minutes with no result event pages Platform. This is the "nothing lost" tripwire.
- **State lives in:** the monolith DB for row status. The broker carries only messages and results.
- **If something fails:**
  - **The relay dies after Phase A.** The row is `publishing` and its lease expires. The sweep republishes it.
  - **The relay dies after the broker stored the message but before Phase C.** The sweep republishes, and the service dedups.
  - **A result event is lost or the consumer is down.** The service's DB is authoritative for sending. Only the monolith's copy lags, and the watchdog alert covers it.
  - **A flag flips back to `monolith` mid-flight.** `publishing` and `published` rows stay with the service, and the old worker never selects them.
- **Gate:** every flag is still `monolith`, so this step changes no production behavior. Confirm that the relay claims zero rows.

### 5. Staging rehearsal of every failure and of rollback

- **Starts when:** steps 3 and 4 are deployed to staging against a fake MailRelay that honors `idempotency_key` with a 24 h memory.
- **What moves:** synthetic notifications of all three types, including `password_reset`, at 5x production rate.
- **State lives in:** staging copies of both databases and the broker. They are separate databases, as in production.
- **Drills.** Each must end with every enqueued notification either sent exactly once, or failed and paged exactly once:
  - kill the monolith relay at each phase
  - kill the service sender between the MailRelay call and its commit
  - redeliver every broker message twice and out of order
  - take the broker down for 10 minutes
  - make the fake MailRelay return errors or time out for 20 minutes, to exercise the failed-and-paged path
  - flip a type's flag to `service` and back to `monolith` repeatedly under load, and at each flip check that the fake MailRelay received exactly one accepted send per id
  - confirm that a flip takes effect within 15 s (10 s flag propagation plus a 5 s poll), which is under the 1 minute limit
- **If something fails:** fix and re-run all drills. Do not proceed with any open duplicate or lost notification.

### 6. Deploy the service to production (receives nothing yet)

- **Starts when:** step 5 passes.
- **What moves:** nothing. The service is deployed with its database, consumer, sender and dashboards, and sits idle.
- **Dashboards and alerts to have live before any flip:**
  - enqueue-to-MailRelay latency, p50 and p99, per type. The clock starts at the monolith `created_at` carried in the message, so assume clock skew between the two systems is well under a second.
  - oldest pending age
  - consumer lag
  - failed count
  - broker-confirm errors
  - the step 4 watchdog
- **State lives in:** the service's production DB.
- **If something fails:** users are unaffected, because no flag is set to `service`.

### 7. Cut over `shipping_update` (earliest day D)

- **Starts when:** step 6 is healthy. Choose a low-traffic period and have the on-call engineer present.
- **What moves:**
  1. Flip `notifications.route.shipping_update = service`.
  2. New `shipping_update` rows (about 40,000 a day) are claimed by the relay and published.
  3. The service sends them.
  4. Rows already `pending` at the flip, including ones waiting out a retry delay, are claimed by the relay and carry their attempt count. Rows the old worker has already locked finish on the old worker. Either way each row has one owner.
- **State lives in:** the monolith DB for the record, and the service DB for the work.
- **If something fails:**
  - **A crash, broker outage, MailRelay outage or redelivery.** Same as steps 3 and 4. Broker downtime does not use up attempts. Only MailRelay failures do.
  - **Rollback.** Flip the flag back to `monolith`. It takes effect within about 15 s. Rows in `publishing` or `published` stay with the service and drain there. Only rows still `pending` return to the old worker. Nothing is lost or re-sent. Leave the service running until its `pending` count is 0.
- **Rollback triggers:** a failed-notification rate above today's baseline, any duplicate report, oldest-pending age over 15 minutes, or a watchdog alert that cannot be explained.

### 8. Soak `shipping_update` for at least 3 days (earliest D to D+3)

- **Starts when:** step 7 is complete.
- **What moves:** nothing. Observe.
- **Exit criteria, all required:**
  - zero duplicate-email reports for `shipping_update`
  - monolith `published` rows reconcile with service `sent` + `failed` + in-flight counts
  - every `failed` row was paged
  - latency and lag are stable
  - no unexplained watchdog alerts
  - monolith CPU and DB connection use from notification sending has dropped for this type
- **If something fails:** roll back as in step 7, fix, and restart the 3-day clock.

### 9. Cut over `order_confirmed` (earliest D+3)

- **Starts when:** step 8's exit criteria are met.
- **What moves:** flip `notifications.route.order_confirmed = service` (about 12,000 a day). Mechanics and failure behavior are identical to step 7.
- **State lives in:** as in step 7.
- **If something fails:** as in step 7, with a per-type rollback flip. `shipping_update` stays on the service during an `order_confirmed` rollback.

### 10. Soak `order_confirmed` for at least 3 days and check the latency gate (earliest D+3 to D+6)

- **Starts when:** step 9 is complete.
- **What moves:** nothing. Observe.
- **Exit criteria, all required:**
  - the step 8 criteria, applied to `order_confirmed`
  - **p99 enqueue-to-MailRelay latency under 60 s on `order_confirmed` over the full soak window.** Measure every row, including retried ones, and record the percentile both with and without retried rows. This is the gate for `password_reset`, which has the 60 s requirement. If the gate is missed, tune the relay and sender poll intervals and measure again over a fresh window.
- **If something fails:** `password_reset` does not move.

### 11. Cut over `password_reset` (earliest D+6)

- **Starts when:** step 10's gates are met, including p99 under 60 s.
- **What moves:** flip `notifications.route.password_reset = service` (about 1,500 a day), with on-call watching.
- **State lives in:** as in step 7.
- **If something fails:**
  - **Rollback triggers:** the step 7 triggers, plus `password_reset` p99 over 60 s for 15 minutes.
  - **Rollback.** Flip the flag back. Rows the service already holds drain there, and no email is lost or sent twice.

### 12. Soak `password_reset` for 7 days (earliest D+6 to D+13)

- **Starts when:** step 11 is complete.
- **What moves:** nothing. All three types run on the service. The old worker stays deployable and the flags still work, so rollback remains a flag flip.
- **Exit criteria:** the step 8 criteria for all three types, plus `password_reset` p99 under 60 s on every day.
- **If something fails:** roll back the affected type. The 7-day clock restarts when it moves again.

### 13. Decommission the old worker (earliest D+13)

- **Starts when:** `password_reset` has run on the service for 7 days with the exit criteria met.
- **What moves, as two separate deploys:**
  1. Stop starting `run_worker` on monolith instances. The relay now claims every `pending` row regardless of flag. Overlap during the rolling deploy is safe because of the single-owner row claim.
  2. Once deploy 1 has been stable for a day, remove `run_worker`, the monolith's `templates` entries for these types, the three routing flags and the flag filter.
- **State lives in:** `enqueue_notification` and the `notifications` table stay, and callers are unchanged. Service-owned state lives in the service DB.
- **If something fails:** rollback is no longer a flag flip. It means redeploying the previous release, which is why the 7-day soak comes first.

---

## Rollback summary (applies to steps 7, 9 and 11)

- **Action:** set the type's flag to `monolith`. It takes effect within about 15 s.
- **Nothing lost.** Rows already handed to the service finish there. Only rows still `pending` go back to the old worker.
- **Nothing re-sent.**
  - Each row has a single owner, enforced by the status claim.
  - The service dedups by id.
  - Both sides send with `idempotency_key = id`.
- **Leave the service running** until its `pending` count for that type is 0.