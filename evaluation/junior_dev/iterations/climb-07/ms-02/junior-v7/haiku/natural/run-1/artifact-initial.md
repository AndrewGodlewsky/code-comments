# Notification Service extraction: shipping plan

## Summary

Callers keep calling `enqueue_notification(tx, ...)` inside their own transaction. That function is unchanged. The `notifications` row is the outbox. A publisher in the monolith hands each row to the broker after the row has committed. The service keeps its own database and sends through MailRelay with the notification id as the idempotency key. Each notification has exactly one owner, the side that claims its row first, and that ownership never changes.

Duplicates are blocked at three layers:

1. **MailRelay key.** Any send with the same id is dropped for 24 hours. This covers retries and crash recovery.
2. **Service inbox.** The inbox primary key is the notification id. A redelivered message is ignored, and a terminal row only re-emits its outcome.
3. **In-doubt rule.** A claim left unfinished for more than 12 hours is failed and paged, never resent. This keeps every resend inside MailRelay's 24-hour window.

## Invariants used by every step

- **Single owner.** `notifications.route` is NULL until a sender claims the row. The claim sets it to `monolith` or `service` and never changes it. The monolith worker claims only rows where `route` is NULL or `monolith`. The publisher claims only rows where `route` is NULL. Both use `FOR UPDATE SKIP LOCKED`, so no row can be sent by both sides.
- **Routing flags.** `notifications.route.<type>` is a monolith runtime flag with values `monolith` or `service`. Its default is `monolith`. Only the monolith reads it. The service never reads flags and never reads the monolith database.
- **Ack after commit.** The service acknowledges a message only after its inbox insert has committed. The consumer does a single insert, far below the 30 s redelivery deadline.
- **Outcome events.** The service writes each terminal outcome to an outbox table in the same transaction as the status change. A publisher relays those to an outcome topic. The monolith consumes the topic to set `notifications.status` and `outcome_at`. Because the broker is the only channel, this is also how the monolith reconciles against the service.
- **Paging.** Only the side that owns a row pages on its failure. The service pages for service-owned rows. The monolith pages for monolith-owned rows.
- **Retry policy.** Unchanged on both sides: `MAX_ATTEMPTS = 5`, backoff of 1, 2, 4, 8 minutes, then `failed` and page. `attempts` increments per send, as in the current `_deliver`.
- **Timing budget for the p99 gate.** About 5 s publisher poll, plus broker time, plus about 5 s service poll, plus MailRelay latency. This stays well under 60 s if MailRelay's own p99 is in the low tens of seconds.

## Schema changes

**Monolith `notifications`:**
- `route`: NULL, `monolith`, or `service`.
- `claimed_at`: set when a sender claims a row for an attempt. Cleared when a retry is scheduled or the row is terminal.
- `handed_off_at`: set when the publisher commits a broker handover.
- `outcome_at`: set when the service's outcome event is applied.

**Service database:**
- `inbox`: `notification_id` (primary key, equal to the monolith id), `type`, `user_id`, `email`, `payload`, `status` (`queued`, `sending`, `sent`, `failed`), `attempts`, `next_attempt_at`, `claimed_at`, `last_error`, `received_at`, `updated_at`.
- `outcome_outbox`: `id`, `notification_id`, `status`, `attempts`, `accepted_at` (MailRelay accept time), `published_at`.

Retention: inbox and outcome rows are kept at least 30 days. Republish and redelivery windows must stay shorter than this.

## Steps

### 1. Pass the idempotency key on the old worker and commit per row

- **Starts:** normal deploy to all monolith instances. Nothing else in the system changes yet.
- **Data moves:** none. Each `mailrelay.send` now passes `idempotency_key = row.id`. The worker commits after each row instead of once per batch.
- **State lives:** the monolith `notifications` table, schema unchanged in this step. The dedupe state lives in MailRelay.
- **On failure:**
  - A crash now loses at most one row of progress. A row re-sent after a crash is dropped by MailRelay if the same key was accepted within 24 hours.
  - If MailRelay rejects the key format, sends fail, retries run, and rows end in `failed` with a page. Revert the deploy. Verify the key format in staging first.
  - There is no broker yet, so no redelivery applies.
- **Gate:** support's duplicate-email count (about 30 per week) falls to near zero over one week.

### 2. Add routing columns, the claim lease, and the publisher, with all types on the monolith

- **Starts:** migration adds the four columns above, all NULL. Create `notifications.route.<type>` = `monolith` for all three types. Deploy the publisher in inactive mode. It publishes nothing because no type is routed to `service`.
- **Data moves:** none.
- **Monolith worker, new claim flow:**
  1. In a committed transaction, select pending rows with `route` NULL or `monolith` and due, using `FOR UPDATE SKIP LOCKED`. Set `route = 'monolith'` and `claimed_at = now()`, then commit.
  2. Render and send with the key, outside any open transaction.
  3. In a second transaction, record the result. On success, set `status = 'sent'` and clear `claimed_at`. On a retryable failure, set `attempts`, `next_attempt_at`, and clear `claimed_at`. On the final failure, set `failed` and page.
- **In-doubt rule:** a row with `claimed_at` older than the lease (5 minutes, which must exceed the MailRelay timeout) is re-claimable. If `claimed_at` is more than 12 hours old, mark the row `failed` and page instead of resending.
- **State lives:** the monolith table, which is the only store for monolith-owned rows.
- **On failure:**
  - A crash after the claim commit but before the send leaves an expired lease. The next claim resends with the same key, within 24 hours.
  - A crash after the send but before the result commit does the same.
  - Rendering errors are handled in open decision 2.

### 3. Stand up the Notification Service with no traffic, and port the templates

- **Starts:** deploy the service with its own database and the `inbox` and `outcome_outbox` tables. Its broker consumer subscribes to the `notifications.v1` topic, which has no messages yet.
- **Data moves:** none in production. The templates are ported. The service renders from `payload` at send time, as today.
- **Parity check:** golden tests render each type from sample payloads on both the monolith and the service and require identical subject and body.
- **On failure:** nothing is live. A parity mismatch blocks step 4.

### 4. Dry run on the service (recommended addition)

- **Starts:** the monolith publisher copies each newly enqueued row of all three types to `notifications.shadow.v1`. The copy is published only, with no route change, no claim, and no status change.
- **Data moves:** a copy of each row, including the email and payload, goes to the broker and into a dry-run inbox on the service.
- **Behaviour:** the dry-run service renders and stores the output hash. It has no MailRelay credentials in this environment, so it cannot send. The monolith records a hash of its own render on each send. The two hashes are compared per notification id.
- **Gate:** at least 3 days with zero render mismatches, and a measured enqueue-to-service-ready latency baseline.
- **On failure:** shadow messages can be lost without customer impact, since this is a dry run. The main risk is an accidental send. Prevent it by keeping MailRelay credentials out of the shadow environment.

### 5. Turn on the outcome path

- **Starts:** the service starts its outcome publisher. The monolith starts its outcome consumer, which updates `status` and `outcome_at` for rows with `route = 'service'`, and only moves `status` forward.
- **Data moves:** `{notification_id, status, accepted_at}` events from the service to the monolith.
- **On failure:** the consumer is idempotent, so duplicates are harmless. A lost event is covered by republish (step 6) and by the reconciliation job.

### 6. Cut over `shipping_update`

- **Starts:** set `notifications.route.shipping_update = service`. The change reaches monolith instances within 10 seconds.
- **Publisher, per batch, in one transaction:**
  1. Select route-NULL rows of the type, `FOR UPDATE SKIP LOCKED`.
  2. Set `route = 'service'` and `handed_off_at = now()`.
  3. Publish each row with message id = notification id, and wait for broker confirmation.
  4. Commit.
- **Service consumer:** insert into `inbox` with `ON CONFLICT DO NOTHING`, commit, then ack.
- **Service worker:** claim `queued` rows due now with a lease, render, send with key = id, apply the same retry policy, and write the result and an outcome outbox row in one transaction.
- **Republish:** if a handed-off row has no outcome after 1 hour, the publisher republishes it. It does this hourly until the row is 7 days old, then pages on-call and stops.
- **Duplicate handling:** a duplicate message for a row that is already terminal makes the service re-emit its outcome if one is missing, then ack. It never sends again.
- **Old worker:** it skips `service`-routed rows automatically through its claim filter.
- **On failure:**
  - **Broker down:** rows stay route-NULL in the monolith. Nothing is lost. A backlog-age alert fires after 5 minutes.
  - **Publisher crashes after publish but before commit:** the transaction rolls back, the row is republished later, and the inbox absorbs the duplicate.
  - **Service database down:** the consumer does not ack, so the broker redelivers after 30 s. The broker's retention must exceed the longest service outage. This value is not in the brief (see open decision 4).
  - **Service crashes after insert but before ack:** redelivery hits the unique key and is acked.
  - **MailRelay down:** the service retries on 1, 2, 4, 8 minutes, then marks `failed` and pages.
  - **Redelivery after terminal status:** no send, outcome re-emitted if needed, ack.

### 7. Soak `shipping_update` for at least 3 days

- **Gate:** zero in-doubt rows, zero route-NULL rows older than 5 minutes, zero unresolved service-owned rows past their republish window, and a clean reconciliation.
- **Reconciliation:** the monolith compares its route-`service` rows with outcome events. A row with no outcome after 7 days is paged.

### 8. Cut over `order_confirmed`

- **Starts:** the same as step 6, but for `order_confirmed`. It runs at least 3 days after step 6 has passed its gate.
- **Measurement:** the service records `accepted_at - created_at` for each notification. Use NTP-synced clocks. Clock skew is far smaller than the 60 s target.
- **On failure:** same table as step 6.

### 9. p99 gate before `password_reset`

- **Gate:** over the full `order_confirmed` bake on the service, p99 of enqueue-to-MailRelay-accept is under 60 seconds, with a sufficient sample count.
- **If the gate fails:** do not move `password_reset`. Run the rollback procedure for `order_confirmed` and investigate.

### 10. Cut over `password_reset`

- **Starts:** the same mechanics as step 6. The 7-day decommission clock starts here.
- **Old worker:** remains deployable. It is the rollback path for all three types until decommission.

### 11. Decommission after 7 days on `password_reset`

- **Preconditions:**
  - Zero monolith-owned rows pending.
  - Zero in-doubt rows.
  - A clean reconciliation over the 7-day window.
  - No rollback in progress.
- **Removal:** delete the old worker from the monolith, the three `route` flags, and the monolith's template code and worker-only alert calls.
- **Kept:** the monolith publisher and the outcome consumer. The monolith is still the enqueue point and still the first place a notification is recorded.
- **After this:** rollback to the monolith is no longer possible.

## Rollback procedure (any type, any step before decommission)

1. Set `notifications.route.<type> = monolith`. The change takes effect within 10 seconds.
2. The publisher stops claiming that type. The monolith worker claims route-NULL rows of that type within its next 5-second poll. Expect full effect within one minute.
3. Rows already handed off stay on the service. They are sent there, not recalled, and not re-sent. Each row has exactly one owner, so nothing is duplicated.
4. Rows the service has not yet claimed continue in the broker and inbox. They finish on the service.
5. If the service is down, handed-off rows wait in the broker and inbox. They are paged by age, not dropped.
6. Recall of queued rows is not offered. Recalling a message the service might still process would risk a duplicate.

## Open decisions for the owner

1. **Payload contents.** `password_reset` payloads may contain reset tokens. Those would sit in plaintext on the broker and in the service database. Decide whether to minimise the payload, encrypt it, or keep the token out of the message.
2. **Rendering errors.** Today a render exception inside `_deliver` escapes the transaction and the batch repeats forever. Recommended: count a render error as a failed attempt, so the row reaches `failed` and pages instead of blocking the worker. This changes current behaviour.
3. **In-doubt threshold.** The 12-hour threshold assumes MailRelay's 24-hour key window holds exactly as documented. Confirm this with MailRelay before relying on it.
4. **Broker retention.** The brief does not state retention. It must exceed the longest tolerated service outage. Otherwise messages expire and only the republish path recovers them.
5. **Inbox and outcome retention.** Recommended at least 30 days. This must exceed the 7-day republish cap plus margin.
6. **Shadow dry run.** Step 4 is my addition. Drop it if the 3-day parity and latency data is available another way.
7. **Monolith status updates.** The outcome consumer (step 5) keeps the monolith table, and support tooling that reads it, accurate for service-owned rows. It is also what makes reconciliation possible without a direct database link.