# Plan: extract notifications into a Notification Service

## Summary of the design

**Ownership of a notification.** Every row in the monolith `notifications` table has exactly one owner at any moment. Ownership changes only through an atomic row-status transition, never through the flag.

```
pending ──(old worker locks row, sends)──────────► sent | failed        [owner: monolith]
pending ──(relay claims row)──► publishing ──(broker confirm)──► published   [owner: service]
published ──(result event from service)──► sent | failed                [monolith copy, informational]
```

- **Handoff is one-way.** Once the relay moves a row to `publishing`, the monolith worker never touches it again. The old worker selects only `pending` rows.
- **The flag routes new work only.** `notifications.route.<type>` is `monolith` (default) or `service`. It decides who claims rows still in `pending`. It never moves a row back.
- **Rollback is safe.** A rollback flip therefore cannot cause a double send. Rows already handed to the service finish there. The service keeps running at full capacity for every type even when the flag says `monolith`.
- **Flag skew is safe.** Monolith instances can disagree about the flag for up to 10 s. The row-status claim, with `FOR UPDATE SKIP LOCKED` on both sides, keeps that harmless.
- **Layered duplicate protection.**
  1. Single ownership per row.
  2. The service dedups inbound messages by notification id (primary key).
  3. Every send passes `idempotency_key = notification id`. MailRelay drops repeats for 24 h, and the longest retry chain is 1+2+4+8 = 15 min.
- **Broker handoff message.** It carries `id, type, user_id, email, payload, created_at, attempts, retry_after_seconds`. A row that is mid-backoff keeps its attempt count, so the 5-attempt policy is exact across a handoff. `retry_after_seconds` is a relative delay, so clock skew does not matter.
- **Retry constants.** Both sides use the same `MAX_ATTEMPTS = 5` and `BACKOFF_MINUTES = [1, 2, 4, 8]`. A shared test table asserts they match.
- **Observed problem in today's worker.** `templates.render` runs outside the `try`. A render exception rolls back the whole batch, and the same rows are picked again forever. The service avoids this by rendering inside the retry handling, so a render error counts as a failed attempt. The old worker is left as is, because it is being removed. Step 1 does not change it.

---

## Steps

### 1. Pass the idempotency key from the old worker (ships alone, first)

- **Starts when:** immediately. It needs no other step and is the prerequisite for everything else.
- **What moves:** one change in `_deliver`: `mailrelay.send(..., idempotency_key=row.id)`. No schema or flag changes.
- **State lives in:** the monolith `notifications` table, as today. MailRelay holds the 24 h key memory.
- **If something fails:**
  - **Instance dies after MailRelay accepted part of a batch but before commit.** Those rows stay `pending` and are re-sent as today. MailRelay now drops the repeat and returns success, so the row is marked `sent` with no second email. This should remove the roughly 30 duplicates a week.
  - **MailRelay timeout where it actually accepted the send.** The retry reuses the key, so it is dropped.
  - **MailRelay down.** Behaviour is unchanged. After 5 attempts the row is marked failed and on-call is paged.
- **Exit check:** the weekly duplicate-email count from Support falls to about zero. Keep watching it, because it is the baseline for every later step.

### 2. Monolith groundwork: statuses, routing flags, filtered worker (additive, all types still on the monolith)

- **Starts when:** step 1 is deployed everywhere.
- **What moves:**
  - Additive migration: new statuses `publishing` and `published`, plus nullable `published_at` and `lease_until` columns. Existing rows and code are unaffected.
  - Three flags, `notifications.route.shipping_update`, `.order_confirmed` and `.password_reset`, all defaulting to `monolith`.
  - The worker query gains `AND type = ANY(<types currently routed to monolith>)`. It reads the flags once per poll.
  - `enqueue_notification` is unchanged. Callers do not change.
- **State lives in:** the monolith DB for rows, and `flags.get` for routing.
- **If something fails:**
  - **Rolling deploy has old and new code side by side.** All flags are `monolith`, so both versions do the same thing.
  - **Flag read fails.** The worker defaults to `monolith` for every type, which is today's behaviour.
- **Gate:** do not move on until 100% of instances run this version. No flag may be set to `service` before then. The filter must be present on every instance first, so an old-code instance cannot send rows the service has been told to own.

### 3. Build the Notification Service (own deployment, own database, staging only)

- **Starts when:** can run in parallel with steps 1 and 2. Nothing in production depends on it yet.
- **What moves, and where state lives:** in the service's own database. The service never connects to the monolith DB.
  - `inbox_notifications` has primary key `id`. It holds `type, user_id, email, payload, created_at, attempts, next_attempt_at, status (pending|sent|failed), accepted_at`.
  - `result_outbox` holds the `sent`/`failed` events waiting to go out.
  - `page_pending` is a flag on a failed row, recording that on-call has not yet been paged.
  - **Consumer.** It subscribes to `notifications.send` and does only `INSERT ... ON CONFLICT (id) DO NOTHING` in a transaction, then acks. It never calls MailRelay, so it always acks well inside the broker's 30 s redelivery window. The first attempt is triggered right after insert, not left to a poll, to keep latency low.
  - **Sender.** Per row, in its own transaction: select `FOR UPDATE SKIP LOCKED` where `status='pending' AND next_attempt_at <= now()`. Then render the template (now owned by the service, in the same `try` as the send), then call `mailrelay.send(..., idempotency_key=id)`. On success, set `sent` and `accepted_at` and write a `result_outbox` row in the same transaction. On error, apply the identical policy: attempts below 5 get backoff 1/2/4/8 minutes. On the fifth failure the row is marked `failed`, a result event is written, and `page_pending` is set. After commit the service calls `alerts.page_oncall` and clears `page_pending`. A sweeper re-pages any row left with `page_pending` set.
  - **Result publisher.** It publishes `result_outbox` rows to `notifications.result`, deletes each row after the broker's confirmation, and republishes unconfirmed rows.
  - **Retention.** Keep inbox rows for 30 days, which is longer than any plausible redelivery or replay window.
  - **Tests.** Golden-file tests compare the service's rendered subject and body with the monolith's `templates.render` output for recorded payloads of all three types. A table-driven test asserts the attempt and backoff sequence matches the old worker.
- **If something fails:**
  - **Service dies after the sender's MailRelay call but before commit.** The row is still `pending`, so it is retried. MailRelay drops the repeat via the key, since the retry is minutes away, well inside 24 h.
  - **Service dies after insert but before ack.** The broker redelivers, possibly to another consumer. The primary-key conflict makes it a no-op.
  - **MailRelay down.** The retry policy applies and the attempt counter advances exactly as today.
  - **Broker down.** The service cannot receive new work or publish results. Already-received rows keep sending. Results queue in `result_outbox` and flow when the broker returns.
  - **Residual risk, stated plainly.** If the service is down for more than 24 h after MailRelay accepted a send but before commit, the later resend falls outside the dedup window and could duplicate. Page on-call when the oldest `pending` row's age exceeds 1 hour, so this stays far from 24 h.

### 4. Monolith relay and result consumer (deployed dark: no type routed yet)

- **Starts when:** steps 2 and 3 are done.
- **What moves:**
  - **Relay, a background job on the monolith.** It runs every 1 s and covers only types whose flag is `service`. Phase A is the claim: in one short transaction, `UPDATE ... SET status='publishing', lease_until=now()+30s` on a batch of `pending` rows chosen with `FOR UPDATE SKIP LOCKED` (so it skips any row the old worker has locked), then commit. Phase B publishes each claimed row to `notifications.send` and waits for the broker confirmation. Phase C sets `status='published', published_at=now()` for confirmed rows.
  - **Recovery sweep.** Rows stuck in `publishing` past `lease_until` are republished. Duplicates are harmless because the service dedups by id. This is how a relay crash between claiming and publishing loses nothing.
  - **Broker outage.** After a failed publish the relay stops claiming new batches until a publish succeeds. At most one batch is therefore stranded in `publishing` during an outage.
  - **Result consumer.** It reads `notifications.result` and runs `UPDATE notifications SET status = <sent|failed> WHERE id = %s AND status IN ('published','publishing')`. It is idempotent, so redelivery is harmless.
  - **Watchdog alert.** Any row in `published` or `publishing` for more than 30 minutes with no result event pages Platform. This is the "nothing lost" tripwire.
- **State lives in:** the monolith DB for row status. The broker carries messages and results only.
- **If something fails:**
  - **Relay dies after Phase A.** The row is `publishing` and the lease expires. The sweep republishes it.
  - **Relay dies after the broker stored the message but before Phase C.** The sweep republishes. The service dedups.
  - **Result event is lost or the consumer is down.** The service's DB is authoritative for sending. Only the monolith's copy lags, and the watchdog alert covers it.
  - **Flag flips back to `monolith` mid-flight.** `publishing` and `published` rows stay with the service. The old worker never selects them.
- **Gate:** every flag is still `monolith`, so this step changes no production behaviour. Confirm the relay claims zero rows.

### 5. Staging rehearsal of every failure and of rollback

- **Starts when:** steps 3 and 4 are deployed to staging against a fake MailRelay that honours `idempotency_key` with a 24 h memory.
- **What moves:** synthetic notifications of all three types at 5x production rate, including the `password_reset` type.
- **State lives in:** staging copies of both databases and the broker. They are separate databases, as in production.
- **Drills, each of which must end with every enqueued notification sent exactly once or failed and paged exactly once:**
  - kill the monolith relay at each phase
  - kill the service sender between the MailRelay call and its commit
  - redeliver every broker message twice and out of order
  - take the broker down for 10 minutes
  - make the fake MailRelay return errors or time out for 20 minutes, to exercise failed and paged
  - flip a type's flag to `service` and back to `monolith` repeatedly under load
  - at each flip, check that the fake MailRelay received exactly one accepted send per id
  - confirm a flip takes effect within 15 s (the 10 s flag propagation plus a 5 s poll), which is under the 1 minute limit
- **If something fails:** fix and re-run all drills. Do not proceed with any open duplicate or lost notification.

### 6. Deploy the service to production (receives nothing yet)

- **Starts when:** step 5 passes.
- **What moves:** nothing. The service is deployed with its database, consumer, sender and dashboards, and it is idle.
- **Dashboards and alerts to have live before any flip:**
  - enqueue-to-MailRelay latency, p50 and p99, per type. The clock starts at the monolith `created_at` carried in the message, so assume NTP skew well under a second.
  - oldest pending age
  - consumer lag
  - failed count
  - broker-confirm errors
  - the step 4 watchdog
- **State lives in:** the service's production DB.
- **If something fails:** it has no effect on users, because no flag is on `service`.

### 7. Cut over `shipping_update` (earliest day D)

- **Starts when:** step 6 is healthy. Choose a low-traffic period and have the on-call engineer present.
- **What moves:**
  1. Flip `notifications.route.shipping_update = service`.
  2. New `shipping_update` rows (about 40,000 a day) are claimed by the relay and published.
  3. The service sends them.
  4. Rows already `pending` when the flip happens, including ones mid-backoff, are claimed by the relay and carry their attempt count. Rows the old worker has already locked finish on the old worker. Either way there is one owner per row.
- **State lives in:** the monolith DB for the record and the service DB for the work.
- **If something fails:**
  - **Crash, broker down, MailRelay down or redelivery.** Same as steps 3 and 4. Broker downtime does not use up attempts, only MailRelay failures do.
  - **Rollback, if needed.** Flip the flag back to `monolith`. It takes effect within about 15 s. Rows in `publishing` or `published` stay with the service and are drained there. Only rows still `pending` return to the old worker. Neither loses or re-sends anything. Leave the service running until its `pending` count is 0.
- **Rollback triggers:** a failed-notification rate above today's baseline, any duplicate report, oldest-pending age over 15 minutes, or a watchdog alert that cannot be explained.

### 8. Soak `shipping_update` for at least 3 days (earliest D to D+3)

- **Starts when:** step 7 is complete.
- **What moves:** no change. Observe.
- **Exit criteria, all required:**
  - zero duplicate-email reports for `shipping_update`
  - monolith `published` rows reconcile with service `sent` + `failed` + in-flight counts
  - every `failed` row paged
  - latency and lag stable
  - no unexplained watchdog alerts
  - monolith CPU and DB connection use from notification sending has dropped for this type
- **If something fails:** roll back as in step 7, fix, and restart the 3-day clock.

### 9. Cut over `order_confirmed` (earliest D+3)

- **Starts when:** step 8's exit criteria are met.
- **What moves:** flip `notifications.route.order_confirmed = service` (about 12,000 a day). Mechanics and failure behaviour are identical to step 7.
- **State lives in:** as in step 7.
- **If something fails:** as in step 7, with a per-type rollback flip. `shipping_update` stays on the service during an `order_confirmed` rollback.

### 10. Soak `order_confirmed` for at least 3 days and check the latency gate (earliest D+3 to D+6)

- **Starts when:** step 9 is complete.
- **What moves:** no change. Observe.
- **Exit criteria, all required:**
  - the step 8 criteria, applied to `order_confirmed`
  - **p99 enqueue-to-MailRelay latency under 60 s on `order_confirmed` over the full soak window.** Measure every row, including retried ones, and record the percentile with and without retried rows. This is the gate for `password_reset`, which has the 60 s requirement. If the gate is missed, tune relay and sender poll intervals and re-measure for a fresh window.
- **If something fails:** `password_reset` does not move.

### 11. Cut over `password_reset` (earliest D+6)

- **Starts when:** step 10's gates are met, including p99 under 60 s.
- **What moves:** flip `notifications.route.password_reset = service` (about 1,500 a day), with on-call watching.
- **State lives in:** as in step 7.
- **If something fails:**
  - **Rollback triggers:** include `password_reset` p99 over 60 s for 15 minutes, in addition to the step 7 triggers.
  - **Rollback.** Flip the flag back. Rows the service already holds are drained there, and no email is lost or sent twice.

### 12. Soak `password_reset` for 7 days (earliest D+6 to D+13)

- **Starts when:** step 11 is complete.
- **What moves:** no change. All three types run on the service. The old worker stays deployable and its flags still work, so rollback stays a flag flip.
- **Exit criteria:** the step 8 criteria for all three types, plus `password_reset` p99 under 60 s on every day.
- **If something fails:** roll back the affected type. The 7-day clock restarts when it moves again.

### 13. Decommission the old worker (earliest D+13)

- **Starts when:** `password_reset` has run on the service for 7 days with exit criteria met.
- **What moves, as two separate deploys:**
  1. Stop starting `run_worker` on monolith instances. The relay now claims every `pending` row regardless of flag. Rolling-deploy overlap is safe because of the single-owner row claim.
  2. Once step 1 has been stable for a day, remove `run_worker`, the monolith's `templates` entries for these types, the three routing flags and the flag filter.
- **State lives in:** `enqueue_notification` and the `notifications` table stay, and callers are unchanged. Service-owned state lives in the service DB.
- **If something fails:** a rollback is no longer a flag flip. It means redeploying the previous release, which is why the 7-day soak comes first.

---

## Rollback summary (applies to steps 7, 9 and 11)

- **Action:** set the type's flag to `monolith`. It takes effect within about 15 s.
- **Nothing lost.** Rows already handed to the service finish on the service. Only rows still `pending` go back to the old worker.
- **Nothing re-sent.**
  - Each row has a single owner, enforced by the status claim.
  - The service dedups by id.
  - Both sides send with `idempotency_key = id`.
- **Leave the service running** until its `pending` count for that type is 0.
