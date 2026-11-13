# Notification Service extraction: shipping plan

## Summary

This plan moves notification sending out of the monolith and into a separate Notification Service with its own database, one notification type at a time. Callers keep calling `enqueue_notification(tx, ...)` inside their own transaction, and the monolith `notifications` row stays the first record. A monolith publisher hands each row to the service over the broker, the service sends it through MailRelay and reports the result back.

Each notification has one owner, the side that claims its row first, and that owner never changes. This blocks both lost and duplicate emails. A type moves back to the monolith by a flag change.

## How it works today

Code: `app/notifications.py`, inside the monolith. Owner: Platform team.

`enqueue_notification` inserts a `pending` row inside the caller's transaction, so the row exists only if the caller commits. The monolith worker runs on every instance. Every 5 s it claims up to 50 due `pending` rows, sends each one, and commits once for the whole batch. Each row gets 5 attempts, waiting 1, 2, 4 and 8 minutes before attempts 2 to 5. After the fifth failure the row is `failed` and on-call is paged.

Known problems:
- If an instance dies after MailRelay has accepted some rows but before the batch commit, those rows are sent again. Support sees about 30 duplicate emails a week.
- Sending competes with checkout for monolith CPU and database connections.
- A render exception escapes the transaction, so the batch repeats forever. Open questions covers this.

## Terms

- **Notification types.** Three types, all email only, all sent through MailRelay:
  - `shipping_update`: a carrier webhook updates a shipment. About 40,000 a day.
  - `order_confirmed`: checkout commits an order. About 12,000 a day.
  - `password_reset`: a user asks to reset their password. About 1,500 a day. Its p99 enqueue-to-MailRelay time must be under 60 s.
- **MailRelay.** The email sending service. Its `send()` takes an optional `idempotency_key`. If it has already accepted a send with that key in the last 24 hours, it drops the new send and returns success. Today we pass no key. Its errors include timeouts.
- **Idempotency key.** A value sent with each email so MailRelay can spot repeats. Here it is the notification id.
- **Broker.** The message broker that billing and search already use. It delivers at least once. A message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once a message is stored. Topics: `notifications.v1` (handed-off rows), `notifications.outcome.v1` (outcome events, named by this plan), `notifications.shadow.v1` (step 4 copies).
- **Ack.** A consumer's message to the broker that it has handled a message, so the broker stops redelivering it.
- **Monolith worker (old worker).** `run_worker` in `app/notifications.py`, on every monolith instance. It polls every 5 s and claims up to 50 rows per batch.
- **Publisher.** A monolith process that hands rows to the broker. It polls every 5 s. "Inactive" means it runs but publishes nothing.
- **Service worker.** The sender inside the Notification Service.
- **Route.** The `route` column on a monolith row: `monolith` or `service`. It is NULL until a sender claims the row, and it names the owner.
- **Route flag.** A monolith runtime flag, `notifications.route.<type>`, with value `monolith` or `service`. Default `monolith`. A change reaches every monolith instance within 10 s.
- **Claim.** A sender takes ownership of rows by committing a change to them. It selects rows with `FOR UPDATE SKIP LOCKED`, which locks the rows it takes and skips rows another worker has locked, so nobody waits on or double-takes a row.
- **Lease.** A claim stamps `claimed_at`. The lease is 5 minutes, and it must be longer than the MailRelay timeout. After it expires, any sender may claim the row again.
- **First claim.** The time of a row's first claim. It is never cleared, and the in-doubt rule measures from it.
- **In-doubt.** A row whose first claim is more than 12 hours old and which has no result.
- **Handover.** The publisher's committed change that sets a row's route to `service`.
- **Inbox.** The service's table of received notifications.
- **Outcome outbox.** The service's table of finished outcomes waiting to be published.
- **Outcome event.** A message `{notification_id, status, accepted_at}` that tells the monolith a service-owned row has finished. `status` is `sent` or `failed`.
- **Terminal.** A status that never changes again: `sent` or `failed`.
- **Idempotent.** Safe to apply twice with the same result.
- **Republish.** Publishing a handed-off message again, with the same message id.
- **Reconciliation.** An hourly check in the monolith that compares service-owned rows with outcome events.
- **`INSERT ... ON CONFLICT DO NOTHING`.** An insert that is skipped when its key already exists.
- **p99.** The time that 99 percent of sends beat.
- **NTP.** Network time sync. It keeps clocks on different machines close together.

## How the system runs

### Invariants (apply to every step)

- **Callers do not change.** Business code calls `enqueue_notification(tx, ...)` inside its own transaction. The monolith `notifications` table stays the first place a notification is recorded.
- **Separate data.** The service has its own database. It never touches the monolith database, and the monolith never touches the service database. The broker is the only channel between them.
- **Nothing lost.** Every notification whose enqueuing transaction committed ends up accepted by MailRelay, or marked `failed` with on-call paged.
- **Nothing duplicated.** A user never gets the same notification twice: not after a crash, a redelivery, a cutover or a rollback.
- **Single owner.** The committed claim decides ownership.
  - The monolith worker claims rows with `route = monolith`, or with route NULL when that type's flag is `monolith`.
  - The publisher claims route-NULL rows only when that type's flag is `service`.
  - Both use `FOR UPDATE SKIP LOCKED`.
  - The flag only decides which side tries first. A late-read flag cannot give a row to both sides.
- **Flags.** Only the monolith reads route flags. The service never reads flags or the monolith database.
- **Handover before publish.** The publisher commits a handover before it publishes. So the monolith never sends a row that has a handover.
- **Lease and in-doubt (both sides).** An expired lease can be claimed again, and the resend uses the same key. If a row's first claim is more than 12 hours old and it has no result, the row is marked `failed` and paged. It is never resent, and nobody checks MailRelay for it, so it may already have been delivered. On-call decides. This keeps every resend inside MailRelay's 24-hour window, measured from the first send.
- **Ack after commit.** The service acks a message only after its inbox insert has committed. The insert is one write, far below the 30 s redelivery deadline.
- **Outcome events.** The service writes each terminal outcome to `outcome_outbox` in the same transaction as the status change. The publisher relays those to `notifications.outcome.v1`. The monolith consumer sets `status` and `outcome_at`, moves `status` forward only, and ignores duplicates.
- **Paging.** Only the side that owns a row pages for its failures, through the existing `alerts.page_oncall`.
- **Retry policy (both sides).** `MAX_ATTEMPTS = 5`, waits of 1, 2, 4 and 8 minutes, then `failed` and page. `attempts` increases on each send.
- **Retention.** Inbox and outcome rows are kept at least 30 days. Republish and redelivery windows must be shorter than that.
- **Latency budget.** About 5 s publisher poll, plus broker time, plus about 5 s service poll, plus MailRelay latency. This is well under 60 s if MailRelay's own p99 is in the low tens of seconds.

### Data

Monolith `notifications`, new columns:
- `route`: NULL, `monolith` or `service`.
- `claimed_at`: set when a sender claims a row for an attempt. Cleared when a retry is scheduled or the row is terminal.
- `first_claimed_at`: set on the first claim and never cleared.
- `handed_off_at`: set when the publisher commits a handover.
- `published_at`: set when the broker confirms the publish.
- `outcome_at`: set when the service's outcome event is applied.
- `shadow_published_at`: set when the broker confirms the step 4 copy.
- `render_hash`: hash of the monolith's own render, stored on each send in step 4.

Service database:
- `inbox`: `notification_id` (primary key, equal to the monolith id), `type`, `user_id`, `email`, `payload`, `status` (`queued`, `sending`, `sent`, `failed`), `attempts`, `next_attempt_at`, `claimed_at`, `first_claimed_at`, `last_error`, `received_at`, `updated_at`.
- `outcome_outbox`: `id`, `notification_id`, `status`, `attempts`, `accepted_at` (MailRelay accept time), `published_at`.

### Moved-type flow

This runs for each type after its flag is set to `service`. Steps 6, 8 and 10 use it.

1. **Handover (publisher, one short transaction per batch).** Select route-NULL rows of the type with `FOR UPDATE SKIP LOCKED`. Set `route = service` and `handed_off_at = now()`. Commit. From this commit on, the monolith worker does not send these rows.
2. **Publish.** Publish each committed row to `notifications.v1`, with message id = notification id. The message carries the row's id, type, user id, email and payload. Wait for broker confirmation, then set `published_at`. A handed-off row without `published_at` is published again on the next poll.
3. **Consume (service).** Insert the message into `inbox` with `ON CONFLICT DO NOTHING`, commit, then ack.
4. **Send (service worker).** Claim `queued` rows that are due, and `sending` rows whose lease has expired. Set `status = sending`, `claimed_at`, and `first_claimed_at` if it was NULL. Render from `payload` and send with key = id. Each row is sent and written in its own transaction.
   - On success, set `status = sent`.
   - On a retryable failure, set `attempts` and `next_attempt_at`, clear `claimed_at`, and set `status = queued`.
   - On the final failure, set `status = failed` and page.
   - Write the `outcome_outbox` row in the same transaction as each status change.
5. **Report (service outcome publisher).** Send each `outcome_outbox` row that has no `published_at` to `notifications.outcome.v1`. Set `published_at` after confirmation. Retry unconfirmed rows on the next poll.
6. **Apply (monolith outcome consumer).** For a row with `route = service`, set `status` and `outcome_at`, moving `status` forward only. For a row that is not `service`, do not apply the event. Log it as a mismatch for reconciliation, because applying it would give one row two owners' outcomes.
7. **Republish.** A row that has `published_at` set but no outcome after 1 hour is republished. The publisher does this hourly until the row is 7 days old, counted from `handed_off_at`. Then it pages on-call and stops.
8. **Duplicates.** A duplicate message for a terminal row makes the service re-emit its outcome if one is missing, then ack. It never sends again.
9. **Old worker.** It skips service-owned rows through its claim filter.

While a row is handed off, its monolith `status` stays `pending` until the outcome event arrives. Support sees `pending` with `route = service` and `handed_off_at` set. Users see nothing until the service sends the email.

### What happens when things fail

| What fails | What happens |
|---|---|
| Broker down | The handover still commits, so the row stays service-owned but unpublished. The publisher retries on each poll. Nothing is lost. A backlog-age alert fires after 5 minutes. Open questions asks who raises it. |
| Publisher crashes after handover commit, before publish | The row is published on the next poll after restart. |
| Publisher crashes after publish, before `published_at` is set | The row is published again. The inbox absorbs the duplicate. |
| Service database down | The consumer does not ack, so the broker redelivers after 30 s. The broker's retention must exceed the longest outage. Open questions covers this. |
| Service crashes after inbox insert, before ack | The redelivery hits the unique key and is acked. |
| Sender crashes after claim, before send, or after send, before the result commit (monolith or service) | The lease expires. The next claim resends with the same key, within 24 hours. |
| MailRelay down | Retries wait 1, 2, 4 and 8 minutes, then the row is `failed` and paged. |
| MailRelay slow or times out on one send | That row is a retryable failure. The other rows in the batch continue. The MailRelay timeout must be shorter than the lease. Open questions covers the value. |
| Redelivery after the row is terminal | No send. The outcome is re-emitted if missing. Then ack. |
| First claim more than 12 hours old, no result | Marked `failed` and paged. Never resent. |
| Outcome event lost | Republish (step 7) and reconciliation recover it. |
| Outcome event duplicated | Harmless. The consumer is idempotent. |
| Render error | Open questions covers this. |

## Rollout steps

Steps run in this order. Each step has a gate before the next one starts.

### 1. Idempotency key and per-row commits on the old worker

- **Starts:** a normal deploy to all monolith instances. Nothing else changes yet.
- **Data moves:** none. Each `mailrelay.send` passes `idempotency_key = row.id`. The worker commits after each row, not once per batch.
- **State lives:** the monolith `notifications` table, schema unchanged. The dedupe state lives in MailRelay.
- **On failure:**
  - A crash now loses at most one row of progress. A row sent again after a crash is dropped by MailRelay if the same key was accepted within 24 hours.
  - If MailRelay rejects the key format, sends fail, retries run, and rows end `failed` with a page. Revert the deploy. Verify the key format in staging first.
  - There is no broker yet, so no redelivery applies.
- **Gate:** support's duplicate-email count (about 30 a week) falls to near zero over one week.

### 2. Routing columns, claim flow and publisher, all types on the monolith

- **Starts:** a migration adds the monolith columns listed under Data, all NULL. Create `notifications.route.<type>` = `monolith` for all three types. Deploy the publisher in inactive mode. It publishes nothing, because no type is routed to `service`.
- **Data moves:** none.
- **State lives:** the monolith table, the only store for monolith-owned rows.
- **Monolith worker, new claim flow:**
  1. In one committed transaction, select rows that are due (`next_attempt_at <= now()`), whose claim has expired (`claimed_at` NULL or older than the lease), and whose route is `monolith`, or NULL with that type's flag set to `monolith`. Use `FOR UPDATE SKIP LOCKED`. Set `route = monolith` if it was NULL, set `claimed_at = now()`, and set `first_claimed_at` if it was NULL. Commit.
  2. Render and send with the key, outside any open transaction.
  3. In a second transaction, record the result. On success, set `status = sent` and clear `claimed_at`. On a retryable failure, set `attempts` and `next_attempt_at`, and clear `claimed_at`. The row keeps `route = monolith`, so a flag change never moves its retries to the service. On the final failure, set `failed` and page.
- **On failure:** crashes follow the lease and in-doubt rules, as in the failure table. Render errors are open.

### 3. Stand up the Notification Service with no traffic, and port the templates

- **Starts:** deploy the service with its own database and the `inbox` and `outcome_outbox` tables. Its broker consumer subscribes to `notifications.v1`, which has no messages yet.
- **Data moves:** none in production. The templates are ported, and the service renders from `payload` at send time, as today. The monolith keeps its templates until decommission.
- **Parity check:** golden tests render each type from sample payloads on both the monolith and the service, and require identical subject and body.
- **On failure:** nothing is live. A parity mismatch blocks step 4.

### 4. Dry run on the service (recommended; open questions asks whether to keep it)

- **Starts:** the monolith publisher copies each newly enqueued row of all three types to `notifications.shadow.v1`. It takes rows with `shadow_published_at` NULL and `created_at` after the step 4 deploy, and sets `shadow_published_at` when the broker confirms. The copy is published only. There is no route change, no claim and no status change. The monolith worker still sends the real email, as in step 2.
- **Data moves:** a copy of each row, including email and payload, goes to the broker and into a dry-run inbox on the service.
- **Behaviour:** the dry-run service renders each notification and stores a hash of its output. It has no MailRelay credentials in this environment, so it cannot send. The monolith records a hash of its own render on each send, in `render_hash`. The two hashes are compared per notification id.
- **Gate:** at least 3 days with zero render mismatches, and a measured enqueue-to-service-ready latency baseline.
- **On failure:** shadow messages can be lost without customer impact, since this is a dry run. The main risk is an accidental send, so MailRelay credentials stay out of the shadow environment.

### 5. Turn on the outcome path

- **Starts:** the service starts its outcome publisher. The monolith starts its outcome consumer.
- **Data moves:** `{notification_id, status, accepted_at}` events from the service to the monolith, on `notifications.outcome.v1`.
- **State lives:** the monolith `status` and `outcome_at` for service-owned rows, and the service `outcome_outbox`.
- **On failure:** duplicates are harmless. A lost event is covered by republish and reconciliation.

### 6. Cut over `shipping_update`

- **Starts:** set `notifications.route.shipping_update = service`. The change reaches monolith instances within 10 seconds. The moved-type flow then runs for this type.
- **Data moves:** one message per row, on `notifications.v1`.
- **State lives:** the monolith table until the handover commits, then the service `inbox` and `outcome_outbox`. The broker holds messages in transit.
- **On failure:** the failure table.

### 7. Soak `shipping_update` for at least 3 days

- **Gate:**
  - zero in-doubt rows;
  - zero route-NULL rows older than 5 minutes;
  - zero service-owned rows that are unresolved past their republish window;
  - a clean reconciliation.
- **Reconciliation.** The monolith runs it hourly. It compares route-`service` rows that have `handed_off_at` set with applied outcome events (`outcome_at`). It also reports outcome events for rows that are not `service`. Mismatches go to the Platform team, which owns this code. Rows with no outcome after 7 days are paged by the republish cap.
- **If the gate fails:** the next type does not move until it passes.

### 8. Cut over `order_confirmed`

- **Starts:** set `notifications.route.order_confirmed = service`, at least 3 days after `shipping_update` passed its gate. The moved-type flow then runs for this type.
- **Measurement:** the service records `accepted_at - created_at` for each notification. Clocks must be NTP-synced. Clock skew is far smaller than the 60 s target.
- **On failure:** the failure table.

### 9. p99 gate before `password_reset`

- **Gate:** over the full `order_confirmed` bake on the service, which lasts at least 3 days, p99 of enqueue-to-MailRelay-accept is under 60 seconds, with a sufficient sample count.
- **If the gate fails:** do not move `password_reset`. Roll back `order_confirmed` (see Rollback) and investigate.

### 10. Cut over `password_reset`

- **Starts:** set `notifications.route.password_reset = service`, after step 9 passes its gate. The moved-type flow then runs for this type. The 7-day decommission clock starts here.
- **Old worker:** it stays deployable. It is the rollback path for all three types until decommission.
- **Open:** the payload decision (see Open questions) must be made before this step.

### 11. Decommission after 7 days on `password_reset`

- **Preconditions:**
  - zero monolith-owned rows pending;
  - zero in-doubt rows;
  - a clean reconciliation over the 7-day window;
  - no rollback in progress.
- **Removal:** the old worker, the three `route` flags, the monolith's template code, and the worker-only alert calls.
- **Kept:** the monolith publisher and the outcome consumer. The monolith is still the enqueue point and still the first place a notification is recorded.
- **After this:** rollback to the monolith is no longer possible.

## Rollback procedure (any type, any step before decommission)

1. Set `notifications.route.<type> = monolith`. The change takes effect within 10 seconds.
2. The publisher stops handing over that type. The monolith worker claims route-NULL rows of that type within its next 5-second poll. Expect new route-NULL rows to reach the monolith within one minute of the flip. The flag does not change rows that are already handed off. The publisher keeps publishing rows it already handed over, whatever the flag says.
3. Rows already handed off stay on the service. This includes a handover that committed but is not yet published. They are sent there, not recalled, and not re-sent. Each row has exactly one owner, so nothing is duplicated.
4. Rows the service has not yet claimed continue in the broker and inbox, and finish on the service.
5. If the service is down, handed-off rows wait in the broker and inbox. They are paged by age, not dropped.
6. Recall of queued rows is not offered. Recalling a message the service might still process would risk a duplicate.

## Open questions

1. **Payload contents.** `password_reset` payloads may contain reset tokens. Those would sit in plaintext on the broker and in the service database. Decide whether to minimise the payload, encrypt it, or keep the token out of the message. Decide before step 10.
2. **Render errors.** Today a render exception escapes the transaction and the batch repeats forever. Recommended: count a render error as a failed attempt, so the row reaches `failed` and pages instead of blocking the worker. This changes current behaviour. Not yet decided for the service worker either.
3. **In-doubt threshold.** The 12-hour threshold assumes MailRelay's 24-hour key window holds exactly as documented. Confirm this with MailRelay before relying on it.
4. **Broker retention.** The brief does not state broker retention. It must exceed the longest tolerated service outage. Otherwise messages expire, and only the republish path recovers them.
5. **Inbox and outcome retention.** The plan recommends at least 30 days. This must exceed the 7-day republish cap plus margin.
6. **Shadow dry run.** Step 4 is an addition to the brief. Drop it if the 3-day parity and latency data is available another way.
7. **Support tooling.** Monolith `status` stays `pending` for service-owned rows. Support tooling may need to show `route` and `handed_off_at` beside it.
8. **Backlog-age alert.** The brief does not say which system raises the 5-minute backlog-age alert, or how it measures route-NULL rows and unpublished handovers. It needs an owner.
9. **Dry-run hash comparison.** The brief does not say how the dry-run service's hashes reach the monolith for comparison. The step 4 zero-mismatch gate depends on it.
10. **Send timeout and service batch size.** The brief does not give the MailRelay send timeout, which must be shorter than the 5-minute lease, or the batch size of the service worker.
11. **Sample size for the p99 gate.** "Sufficient sample count" is not defined.