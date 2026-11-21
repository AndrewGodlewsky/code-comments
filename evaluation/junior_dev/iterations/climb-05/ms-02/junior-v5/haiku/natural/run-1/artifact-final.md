# Plan: Extract notifications into a Notification Service

## What this is

Today, business code calls `enqueue_notification(tx, ...)` inside its own database transaction. That writes a `pending` row to the monolith's `notifications` table. A worker on every monolith instance polls that table, renders the email, sends it through MailRelay, and updates the row. Sending uses the same CPU and database connections as checkout, so the two compete.

This plan moves sending for each notification type to a new, separately deployed Notification Service, one type at a time. The enqueue call and the `notifications` table stay. Each row gets a route when it is written: `service` or `monolith`. The old worker keeps sending `monolith` rows. For `service` rows, the monolith publishes each row to a message broker. The service sends the email and reports the result back through the broker. The monolith then sets the row's final status.

The route is set once, at insert, so a flag flip changes only new rows. Rows already in flight finish on the side where they started. That is why rollback neither loses nor re-sends notifications.

Duplicates are blocked in two layers. MailRelay drops a repeat send that uses the same idempotency key within 24 hours. The service's `jobs` table has one row per notification id, so a redelivered broker message does nothing.

## Terms

- **Notification row:** a row in the monolith's `notifications` table. Every notification has one, whichever side sends it.
- **Route:** `service` or `monolith`. It is set at insert from the flag `notify.route.<type>`. A missing flag, or any value other than `service`, means `monolith`.
- **Flag:** a named runtime value that operators set. The monolith reads it with `flags.get(name)`. A change reaches every monolith instance within 10 seconds.
- **Old worker:** today's in-process `run_worker`, running on every monolith instance. After step 2 it sends only `monolith` rows.
- **Outbox relay:** a loop in the monolith that publishes `service` rows to the broker.
- **Status consumer:** a loop in the monolith that reads status events and updates the matching row.
- **Sweeper:** three checks the monolith runs every minute. Each one pages on-call.
- **Broker:** the message broker that billing and search already use. It is at-least-once: a message not acknowledged within 30 seconds is redelivered, possibly to another consumer. A publisher gets a confirmation once the broker has stored the message.
- **Ack:** telling the broker a message is handled, so it is not redelivered.
- **Topic:** a named message stream. `notifications.requested` goes from the monolith to the service. `notification.status` goes back. `notification.summary` carries the daily count.
- **Notification Service:** the new service. It has its own database, and only it uses that database.
- **Job:** one notification's send state, stored as one row in the service's `jobs` table, keyed by notification id.
- **Events outbox:** the service's `events_outbox` table. It holds status events waiting to be published.
- **Lease:** a time-limited claim on a job by one sender. If the sender dies, the lease expires and another sender can claim the job. A lease expiry does not count as an attempt.
- **Row lock (`FOR UPDATE SKIP LOCKED`):** a database lock on a row. Other workers skip locked rows instead of waiting for them.
- **Idempotency key:** a string MailRelay uses to spot repeats. This plan uses the notification's id as the key for every send. If MailRelay already accepted a send with that key in the last 24 hours, it drops the repeat and reports success.
- **Test row:** a notification an operator inserts by hand for the end-to-end check. It goes to a team test mailbox.

## How it runs

### The flow

1. **Enqueue.** Starts when business code calls `enqueue_notification` inside its own transaction. The function reads the flag `notify.route.<type>` and writes one row with `status = 'pending'` and its route. The row exists only if the caller's transaction commits. If the caller rolls back, there is no row and no email, which is correct. If the flag cannot be read, the route is `monolith`, the safe default. For about 10 seconds after a flip, some instances may still read the old value. Both routes are safe, because each side has its own sender and the route never changes after insert.

2. **Publish.** Starts on each cycle of the outbox relay, every 5 seconds, on every monolith instance. In one database transaction, the relay locks the `service` rows where `published_at` is null and `status` is `pending`. It publishes each row to `notifications.requested` as `{id, type, email, payload, created_at}`, keyed by notification id. It waits for the broker's confirmation that the message is stored, then sets `published_at` and commits. The row lock is held until that commit, including the wait. So two relay instances never publish the same row at the same time. If no confirmation arrives, or the relay crashes before the commit, the row stays unpublished and the next cycle publishes it again. The jobs table makes that repeat harmless. If the broker is down, rows wait in the monolith table. The unpublished check pages on-call after 5 minutes. Nothing is lost.

3. **Accept.** Starts when the service's consumer receives a message. In one database transaction, it inserts a `jobs` row with `ON CONFLICT (notification_id) DO NOTHING`. The row holds the message's fields (id, type, email, payload, `created_at`), `status = 'pending'`, `attempts = 0`, `next_attempt_at = now`, and an empty lease. The `created_at` is copied from the message, not set to the receive time, so both sides count a notification on the same day. The consumer acks the message only after this commit. If the job already exists, the insert does nothing and the consumer still acks. If the service crashes before the commit, nothing is stored and the broker redelivers the message.

4. **Send.** Starts when a sender loop finds a due job. Each service instance runs the loop every 5 seconds. The number of instances is an operations choice. The row lock stops two instances from taking the same job.
   - **Claim.** A short transaction selects jobs where `status` is `pending`, `next_attempt_at` is now or earlier, and the lease is empty or expired. It locks the row with `FOR UPDATE SKIP LOCKED`, sets `lease_until` to now plus the lease length, and commits. The lease must be longer than the MailRelay timeout plus a margin.
   - **Send.** No transaction is open during the send. The sender renders the template and calls MailRelay with `idempotency_key` set to the notification id. The lease is the only protection while the send runs.
   - **Success.** In one transaction, the sender sets the job to `sent`, clears the lease, and writes a `sent` event to `events_outbox`.
   - **Failure.** A MailRelay error (this includes timeouts) or a template render error counts the same way. In one update, the sender adds 1 to `attempts` and clears the lease. If `attempts` is now 5, it sets the job to `failed`, writes a `failed` event, and pages on-call. Otherwise it sets `next_attempt_at` to now plus 1, 2, 4 or 8 minutes, for attempts 1 to 4. It writes no event on a retry. A render error counts as an attempt so that a bad template cannot loop forever without ever failing.
   - **Crash mid-send.** The lease expires. The next claim sends again with the same key. MailRelay drops the repeat if it already accepted the first send. The expiry does not count as an attempt. Alerts fire on lease expiries, so a crash loop is visible.

5. **Report.** Starts on each cycle of the service's events loop, every 5 seconds. It publishes unpublished `events_outbox` rows to `notification.status`, keyed by notification id. It marks a row published only after the broker confirms. If publishing fails, it retries on the next cycle. If the monolith is down, the broker holds the messages until they are consumed.

6. **Record.** Starts when the status consumer receives an event. It sets `status` and `attempts` on the notification row where the id matches, the route is `service`, and the status is `pending`. A `sent` event sets `sent`. A `failed` event sets `failed`. A repeated event matches nothing and changes nothing. If the id has no row, or the row is a `monolith` row, nothing matches. In every case the consumer acks the message. Without the ack, the broker would redeliver it forever. A `failed` row is not retried automatically, because the service has already paged on-call. If an event is lost, the row stays `pending` until the stuck-event check pages.

7. **Reconcile.** Starts once a day at 02:00 UTC, for the previous UTC day. The service counts its jobs created that day with status `sent` or `failed`, and publishes that count to `notification.summary`. The monolith counts its `service` rows created that day whose status is not `pending`. When the summary arrives, the monolith compares the two counts and pages on-call if they differ. Neither database reads the other. The broker carries the only data between them. Test rows are skipped on both sides, identified by the team test mailbox.

**The old worker** runs alongside the flow. It is today's worker, now selecting only `monolith` rows. Each cycle it takes up to 50 due rows, oldest first, in one transaction with `FOR UPDATE SKIP LOCKED`. It renders and sends each row with the row id as the idempotency key. On success it sets the row to `sent`. On a MailRelay error, including a timeout, it adds 1 to `attempts`. At attempt 5 it sets the row to `failed` and pages on-call. Otherwise it sets `next_attempt_at` to 1, 2, 4 or 8 minutes later. It commits after each row, not after each batch, so a crash cannot cause a re-send of a row already committed. It catches only MailRelay errors. Other errors still stop its thread, as today. That is an open question.

**The sweeper** runs in the monolith every minute. Each check pages on-call.
- *Unpublished check:* a `service` row is still unpublished 5 minutes after it was created.
- *Stuck-event check:* a `service` row is still `pending` 30 minutes after it was published. Its status event has not arrived. The 30 minutes is longer than the 15-minute retry schedule, so a row in normal retry does not page.
- *Old-worker check:* a `monolith` row is still `pending` 5 minutes after its `next_attempt_at`.

### What happens when things fail

| Failure | What happens | Recovery |
|---|---|---|
| Old worker crashes after MailRelay accepts a send, before commit | The row is sent again | MailRelay drops the repeat (same key) |
| MailRelay down or slow | Sends retry on the backoff schedule, then fail and page | Existing policy. On-call handles failed rows |
| MailRelay times out after the send succeeded | The retry uses the same key | MailRelay drops the repeat |
| Template render error in the service | Counts as a failed attempt | After 5 attempts the job is `failed` and on-call is paged. The user does not get the email |
| Broker down | Monolith rows wait unpublished. The service consumer stops | The relay retries. The unpublished check pages after 5 minutes. Nothing is lost |
| Relay crashes after publish, before commit | The row is published again | The `jobs` key makes the repeat a no-op |
| Service crashes after commit, before ack | Broker redelivers the message | The primary key rejects it. Acked, no send |
| Service crashes mid-send | The lease expires | The next claim sends with the same key. MailRelay drops the repeat. Alert on expiries |
| Broker redelivers a message | Primary key on `jobs` | No-op, acked |
| Status event lost, or status consumer down | The monolith row stays `pending` | The stuck-event check pages after 30 minutes. Reconciliation catches gaps |
| Status event for an unknown id, or a `monolith` row | Nothing matches the update | Acked and dropped |
| Flag service down | `flags.get` returns `monolith` | Safe default |
| Reconciliation mismatch | Pages when the summary arrives | Runbook below |
| Daily summary never arrives | Not detected by the plan yet | Open question |

### Reconciliation runbook

When a reconciliation page fires, on-call works through the mismatched day.

1. On the monolith database, list the `service` rows from that day that are still `pending`, with their `published_at`. Copy their ids.
2. On the service database, look up those ids in `jobs` and `events_outbox`. The ids are copied by hand because neither database can read the other.
3. Act on each id:
   - **No job, `published_at` null:** the relay has not published it. The unpublished check should have paged. Fix the relay. It publishes the row on its next cycle.
   - **No job, `published_at` set:** the message was lost. Clear `published_at` so the relay publishes it again. No send happened, so this cannot duplicate one. This works only while the message is within the broker's retention.
   - **Job `sent` or `failed`, event unpublished:** the events loop publishes it. If it does not, fix the loop.
   - **Job `sent` or `failed`, event published but not applied:** clear the event's `published_at` so it is sent again. The status consumer's guard makes a repeat harmless.
   - **Job `failed`:** already paged. Handle it as a failed notification.

## How we roll it out

Ship these steps in order. Each step says what starts it, what data moves, where the state lives, and what happens when it goes wrong.

### Step 1: Keyed sends and per-row commits on the old worker

- **Starts:** a normal monolith release.
- **Data moves:** none. The old worker passes `idempotency_key=str(row.id)` to MailRelay.
- **State:** the unchanged `notifications` table.
- **Also in this step:** commit after each row instead of after each batch. The per-batch commit causes the known duplicate emails, about 30 a week. A row committed before a crash is not sent again.
- **When it goes wrong:**
  - Crash between a MailRelay accept and the commit: the row stays `pending`. The next run sends it again with the same key, and MailRelay drops the repeat.
  - MailRelay down: the existing retry policy applies, unchanged.
  - Rollback: revert the release. Keys already sent cause no harm.

### Step 2: Route column and route-aware enqueue, all routes set to `monolith`

- **Starts:** a release with a migration. The migration adds `route text not null default 'monolith'`, adds `published_at timestamptz null`, and creates partial indexes on `(route, status)`.
- **Data moves:** none. `enqueue_notification` keeps its signature. It reads `notify.route.<type>` and sets `route`.
- **State:** the monolith table. Flags stay in the monolith.
- **Old worker change:** its select adds `AND route = 'monolith'`, so it never takes `service` rows.
- **Rule:** every monolith instance must run this build before any type is set to `service`. An older build would otherwise send `service` rows through the old worker.
- **When it goes wrong:**
  - Migration fails: nothing deploys.
  - Flag service unavailable: `flags.get` falls back to `monolith`.
  - An older build still running during the rollout selects all pending rows. This is harmless, because no row is `service` yet.

### Step 3: Outbox relay, status consumer and sweeper in the monolith, all inert

- **Starts:** a release. Every row is still `monolith`, so the loops find nothing to do.
- **Once active:** the relay runs the Publish step, the status consumer runs the Record step, and the sweeper runs its three checks.
- **State:** the monolith table only.
- **When it goes wrong:**
  - Publish confirmed, but saving `published_at` fails: the relay publishes again, and the `jobs` key absorbs the repeat.
  - Broker down: rows stay unpublished. They are delayed, not lost.
  - Two relay instances: the row lock stops both from publishing the same row.

### Step 4: Build and deploy the Notification Service, receiving no traffic

- **Starts:** a service repository and deployment, separate from the monolith. The service has its own database and credentials. Nothing in the monolith reads or writes that database.
- **Data moves:** none yet.
- **Contents:** a consumer on `notifications.requested`, a sender, the templates moved from the monolith, an events loop, a daily reconciliation job, and the `jobs` and `events_outbox` tables.
- **Golden tests:** for sample payloads of all three types, compare monolith and service output. The output must be byte-equal, or each diff must be reviewed, before any cutover.
- **When it goes wrong:** the failure cases in the table apply. Templates that diverge are caught by the golden tests.

### Step 5: Verify the service end to end, and rehearse rollback

- **Starts:** a manual operator run after step 4 is deployed.
- **Data moves:** a few test rows. An operator inserts them directly into the monolith table with `route = 'service'` and `type = 'shipping_update'`. That template is already in production. Routing is per type, so flags are not involved. The rows go to a team test mailbox. Run in production first. Repeat in staging with the MailRelay sandbox, if one exists.
- **Checks:**
  - Each test row ends `sent` in the monolith table, through its status event.
  - Kill the service mid-run. MailRelay logs show no duplicate.
  - In staging, flip `notify.route.shipping_update` to `service`, then back. New rows follow the flag within 10 seconds. Rows already on the service finish without a re-send.
- **When it goes wrong:** any duplicate or missing status blocks step 6.

### Step 6: Cut over `shipping_update` (at least 3 days)

- **Starts:** an operator sets `notify.route.shipping_update = service`. This happens only after step 5 passes and every monolith instance runs the step 2 build.
- **Data moves:** new `shipping_update` rows get `route = 'service'`. The relay publishes them, and the service sends them. Existing `monolith` rows still drain through the old worker.
- **State:** the monolith rows are `service` and have `published_at` set. The service's `jobs` table holds the sends.
- **Clock:** the 3 days start when the `monolith` backlog for this type reaches zero.
- **Reconciliation:** runs daily. Any mismatch pages.
- **When it goes wrong:**
  - Service down: rows wait, unpublished or pending. Nothing is lost.
  - Mismatch: follow the runbook. If the cause is not clear, flip the flag back, as in Rollback.

### Step 7: Cut over `order_confirmed` (at least 3 days)

- **Starts:** an operator sets `notify.route.order_confirmed = service`. This happens after `shipping_update` has run 3 days with no reconciliation mismatch.
- **Data moves:** as in step 6, for `order_confirmed`.
- **Latency:** the service records `sent_at - created_at` for every job of this type. `created_at` is the monolith row's time, copied in the message. Track p99 over the 3-day window. Clocks must be NTP-synced. The service also logs its receive time, so clock skew can be checked.
- **Gate:** `password_reset` moves only if p99 is under 60 seconds over this window. If it is not, hold step 8 and investigate.
- **When it goes wrong:** as in step 6. A latency miss does not roll anything back. It holds the next cutover.

### Step 8: Cut over `password_reset` (7 days before decommission)

- **Starts:** an operator sets `notify.route.password_reset = service` after `order_confirmed` meets the latency gate.
- **Data moves:** as in step 6. This is the last type to move.
- **Clock:** 7 days from the flip. This is also the decommission gate.
- **When it goes wrong:** roll back by setting `notify.route.password_reset = monolith`. New reset requests reach the old worker within 10 seconds. Rows already on the service finish there. On-call watches the queue after the flip, because password reset is user-facing.

### Step 9: Decommission the old worker (after 7 days on `password_reset`)

- **Starts:** 7 days have passed with no reconciliation mismatch, and there are zero `route = 'monolith' AND status = 'pending'` rows.
- **Data moves:** none. The `notifications` table stays, because it is the record of every notification.
- **Actions:** remove `run_worker` and the old worker. Remove the flag reads and the `route` default if they are no longer needed. Remove the `notify.route.*` flags.
- **Keep deployable:** the old worker stays deployable until this gate passes. The step 8 rollback depends on it.
- **When it goes wrong:** a `monolith` row that appears after removal and stays `pending` triggers the old-worker check. Restoring the worker is a revert of this step's release.

### Rollback (every type)

1. Set `notify.route.<type> = monolith`. The flag reaches every instance within 10 seconds. The old worker polls every 5 seconds.
2. New rows of that type go to the old worker. Rows already on the service finish there.
3. Service rows are not moved back. A handoff across the broker is not transactional, and it could re-send. Published rows wait in the broker or in the service's `jobs` table until the service runs again. If the service is down for a long time, its queue is the backlog. The fix is to restore the service.
4. Verify with the daily reconciliation.

## Open questions

- **MailRelay errors after acceptance:** what happens when a keyed send returns an error after MailRelay accepted it? The plan assumes a retry with the same key is dropped.
- **Key window scope:** is the 24-hour key window per account or per send type? The plan assumes per account.
- **Broker confirmation timeout:** how long does the relay wait before giving up? Not set. The row lock is held during the wait.
- **Lease length:** it must exceed the MailRelay timeout plus a margin. The docs do not give that timeout.
- **Missing summary:** what happens if the daily summary never arrives? Not decided.
- **False mismatch at 02:00 UTC:** events still in flight can cause a false mismatch. No grace period is set.
- **PII in the broker:** is it acceptable to put email addresses and payloads in the broker, under its retention and access policy?
- **Broker retention:** the retention for `notifications.requested` must be shorter than the 30-day `jobs` retention. Otherwise a very old redelivery could send again. The docs do not state the retention.
- **Jobs retention:** the 30-day `jobs` retention must exceed any relay republish delay, including the runbook's republish case.
- **Old worker errors:** the old worker catches only MailRelay errors. Other errors, such as a template render failure in the monolith, appear to stop its thread. The plan keeps this for the old worker. Decide before step 1 whether to fix it.
- **Products:** which product is the broker, and where is the flag store? The docs do not say.
- **Owners:** nobody is named for the sweeper, the daily reconciliation and its runbook, the latency alerts, or restoring the service after a long outage. Rollback depends on that restore.