# Plan: Extract notifications into a Notification Service

## Summary

Today, business code writes a notification row inside its own transaction. An in-process worker in each monolith instance then sends it through MailRelay. We are moving the sending into a separate Notification Service with its own database. Business code does not change, and the monolith's `notifications` table is still the first place a notification is recorded. The message broker is the only link between the two systems.

Every notification has one owner, `monolith` or `service`. The owner is set when the row is inserted and never changes. A flag per type decides the owner of new rows only. So no row ever changes sender, and rollback never has to move work that is already in flight.

## Terms

- **Owner:** the side that sends a notification, `monolith` or `service`. Set at insert, never changed.
- **Outbox:** the monolith's `notifications` table. The relay reads it and publishes service-owned rows to the broker.
- **Inbox:** the service's table of received notifications, keyed by notification id.
- **Idempotency key:** the notification id, sent with every MailRelay call. MailRelay drops a repeat of a key it accepted in the last 24 hours and returns success.
- **Lease:** a time-limited claim that a sender takes on a row before sending. If the sender dies, the lease expires and another sender can claim the row.
- **Shadow:** the service renders a copy of a monolith row and records a hash of it. It never sends the copy. This checks that both sides render the same email.
- **Retry policy:** 5 attempts. Wait 1, 2, 4 and 8 minutes before attempts 2 to 5. After attempt 5, mark the row `failed` and page on-call. Crash recovery counts as an attempt.

## How the system runs

1. Business code inserts the row in its transaction. The owner comes from the flag. The row exists only if the transaction commits.
2. If the owner is `service`, the monolith relay publishes the row to `notification.requested.v1`, keyed by id. It sets `service_published_at`.
3. The service consumer inserts the message into the inbox with `ON CONFLICT (id) DO NOTHING`, commits, then acks. It never waits on MailRelay, so acks stay well inside the broker's 30-second redelivery window.
4. The service sender claims due rows with a lease, renders the template, and sends with `idempotency_key = id`. It applies the retry policy to the result.
5. The service writes status events (`received`, `accepted`, `failed`) to its own outbox, in the same transaction as each state change. A relay publishes them after commit to `notification.status.v1`.
6. The monolith status consumer moves `service_state` forward and mirrors `sent` or `failed` onto the row. A reconciler re-publishes rows whose status never arrived.

Monolith-owned rows are still sent by the old worker, with the same idempotency key.

Message: `{id, type, user_id, email, payload, created_at, schema_version}`, keyed by `id`.

Inbox columns: `id`, `type`, `user_id`, `email`, `payload`, `mode` (`live` or `shadow`), `state` (`queued`, `sending`, `accepted`, `failed`, `shadow`), `attempts`, `first_attempt_at`, `next_attempt_at`, `lease_expires_at`, `last_error`, `created_at` (the monolith's time), `received_at`.

State lives in three places: the monolith database (outbox), the service database (inbox, status outbox, shadow rows), and the flag store.

### What happens when things fail

| What fails | What happens |
|---|---|
| Service consumer crashes before its commit | No ack. The broker redelivers and the insert succeeds. |
| Consumer crashes after commit, before ack | The redelivery hits `ON CONFLICT`, is acked, and creates no duplicate. |
| Redelivery after the row is final | `ON CONFLICT` makes it a no-op. |
| Service database is down | The consumer does not ack, so messages wait in the broker. Retention must cover the outage. |
| Sender crashes during a send | The lease expires and the row is re-claimed. If `first_attempt_at` is under 23 hours ago, it is re-sent with the same key, and MailRelay drops the duplicate. The reclaim counts as an attempt. If it is 23 hours or more, mark it `failed` and page. |
| MailRelay is down or times out | The retry policy applies. After attempt 5, `failed` and page. A timeout is ambiguous, but the key makes the retry safe. |
| Broker is down | The monolith relay retries and rows stay pending. Service status events wait in the service outbox. |
| A status event is lost | The reconciler re-publishes the row. The service dedupes. |
| A status event is duplicated | Forward-only updates make it harmless. |
| The service is fully dead | The service cannot page for itself. The backlog-age and stuck-status alerts catch it. |

## Rollout, in order

Each step lists what starts it, what it does, what data moves, where state lives, and what happens when it goes wrong.

### Step 1. Confirm platform facts (no code)

- **Starts:** plan approval.
- **Does:** confirm four things.
  - MailRelay honours `idempotency_key` on the real API. Check the 24-hour window and the success response on a duplicate.
  - The broker's retention period and its longest redelivery horizon.
  - Whether the broker dedupes by message id. Do not rely on it.
  - Clock skew between hosts. The latency gate in Step 8 needs it.
- **Data moves:** none. **State:** none.
- **On failure:** if MailRelay does not honour keys, stop. The design depends on it. If broker retention is unknown, the inbox retention cannot be sized, so do not start Step 4.

### Step 2. Pass the idempotency key on the old worker

- **Starts:** deploying `_deliver` with `mailrelay.send(..., idempotency_key=str(row.id))`. This applies to all types, before any type moves.
- **Does:** nothing new. The key is the existing row id.
- **Data moves:** none. **State:** the monolith `notifications` table, unchanged.
- **Effect:** a crash after MailRelay accepts a send, but before the batch commit, re-sends the same key, and MailRelay drops it. This should remove most of the roughly 30 weekly duplicates.
- **On failure:** a key the API rejects counts as a `mailrelay.Error`, so it retries and eventually pages. Roll back the deploy if this persists.
- **Verify:** the duplicate-email support count falls, and MailRelay's duplicate-drop responses are counted.

### Step 3. Add ownership to the outbox and make the worker respect it

- **Starts:** a migration, then a deploy.
- **Does:**
  - Add columns. They are additive, so old code ignores them.
    - `owner`: text, not null, default `monolith`, must be `monolith` or `service`.
    - `service_published_at`, `service_state` (`received`, `accepted`, `failed`), `service_state_at`.
    - `shadow_published_at` and `rendered_sha256`, used in Step 6.
    - A partial index on `created_at` where `owner = 'service'` and `service_published_at` is null.
  - The worker query gains `AND owner = 'monolith'`.
  - `enqueue_notification` reads `flags.get('notifications.owner.<type>')`, defaulting to `monolith`. It writes `owner` in the same `INSERT`. Callers do not change.
- **Data moves:** none. **State:** the monolith database only.
- **Gate:** every monolith instance runs the owner-aware worker before any flag is set to `service`. An older instance without the filter would send service-owned rows.
- **On failure:** if the flag cannot be read, use `monolith`, which is always safe. A crash cannot leave partial state, because the insert and the flag decision are in the caller's transaction. To roll back, revert the code and leave the new columns.

### Step 4. Build the Notification Service, dark

- **Starts:** deploying the service with its own database. Its consumer subscribes to `notification.requested.v1`.
- **Does:**
  - The consumer inserts into the inbox and acks, as described under "How the system runs".
  - The sender claims due rows with a lease of about 60 seconds. That is longer than the MailRelay timeout of about 20 seconds.
  - The sender renders the template with a copy of `templates.render`, sends with `idempotency_key = id`, and applies the retry policy.
  - Sending is off until `send_enabled = true` (Step 7).
  - **Resend guard (new policy, needs sign-off):** a lease-expired row is re-sent only if `first_attempt_at` is under 23 hours ago. This keeps a re-send inside MailRelay's 24-hour window.
  - Keep inbox rows for at least the longer of 30 days and the broker's redelivery horizon. This is the dedupe horizon.
- **Data moves:** the message payload goes into the service database. Nothing goes back to the monolith yet.
- **State:** the service database only.
- **Gate:** staging tests with synthetic messages. They cover a crash at each point, redelivery, and MailRelay faults.
- **On failure:** see the failure table above.

### Step 5. Status back-channel and monolith reconciliation

- **Starts:** the service starts publishing status events. The monolith status consumer and the reconciler start on a timer.
- **Does:**
  - The status consumer sets `service_state` and `service_state_at`. It mirrors `sent` or `failed` onto `status`, so existing support tools keep working. It only moves forward: `received` is lower than `accepted` or `failed`. Replays are harmless.
  - The reconciler re-publishes rows where `service_published_at` is set, `service_state` is null, the row is older than 10 minutes, and it is younger than 7 days. The 7-day limit stays inside the service's dedupe retention.
  - A row stuck with `service_published_at` set and no `service_state` for more than 10 minutes pages on-call.
- **Data moves:** notification ids and states go back to the monolith. No email or payload travels this way.
- **State:** the service status outbox and the monolith row.
- **On failure:** if the broker is down, events queue in the service outbox and go out later. If the service is down, the reconciler republishes stale rows, and the page fires. A lost or duplicated event is handled as in the failure table.

### Step 6. Shadow-run `shipping_update`

- **Starts:** setting `notifications.shadow.shipping_update` on.
- **Does:**
  - The monolith relay publishes a copy of each `shipping_update` row with `mode = shadow` and sets `shadow_published_at`.
  - The monolith keeps sending the row, and writes `rendered_sha256` alongside the send.
  - The service renders the shadow copy and reports its hash in the status event. It never calls MailRelay for shadow rows, because the sender only takes `mode = live`.
  - A dashboard compares the service's hash with `rendered_sha256`.
- **Data moves:** a copy of each row, including the email address. This is the same data that moves at cutover.
- **State:** shadow rows sit in the service inbox with state `shadow`.
- **Gate:** zero unexplained mismatches over at least 24 hours. Freeze template edits for this type until Step 10, or version the templates.
- **On failure:** if the service is down, shadow copies queue. The monolith keeps sending, so users are not affected. If a row is redelivered, the insert stays idempotent, and a shadow row can never reach MailRelay.

### Step 7. Cut over `shipping_update`

- **Starts:** setting `notifications.owner.shipping_update = service`, after the Step 6 gate. Set `send_enabled = true` on the service first.
- **Does:** new rows get `owner = service` within about 10 seconds. The relay publishes them, and the service sends them. Rows that are already monolith-owned finish on the old worker.
- **Data moves:** new rows only, through the outbox, the broker and the service.
- **State:** the flag store, the monolith outbox and the service inbox.
- **Monitor:** enqueue-to-accepted p99, backlog age, the `failed` count and pages. Hold for at least 3 days before Step 8.
- **Rollback:** set the flag back to `monolith`. New rows are monolith-owned within about 10 seconds, and the old worker picks them up on its 5-second poll. Rows already owned by the service keep going through the service, including pending outbox rows. No row is re-owned, so nothing is lost or re-sent. This takes effect within a minute.
- **On failure:**
  - Service down: owned rows queue and latency rises, but nothing is lost. Flip new rows back if the outage is long.
  - Broker down: the relay retries, and rows stay pending.
  - MailRelay down: the retry policy applies, then `failed` and page.
- **Emergency only (needs explicit approval):** a flip does not speed up rows the service already owns. If the service must be bypassed, an operator can re-own rows that have `service_state` null and are under 24 hours old. Re-sending with the same key is safe inside that window.

### Step 8. Cut over `order_confirmed`, and pass the latency gate

- **Starts:** setting `notifications.owner.order_confirmed = service`, after `shipping_update` has run on the service for at least 3 days.
- **Does:** the same as Step 7, with the same rollback.
- **Latency gate:** over at least 3 days on the service, the p99 of `service accepted_at minus monolith created_at` for `order_confirmed` rows must be under 60 seconds. This is the gate for Step 9.
  - The metric includes retries. Any retried row is over 60 seconds, because the first retry waits 1 minute. If MailRelay failures exceed about 1%, the gate fails even when the pipeline is healthy.
  - Recommended: gate on this strict metric, and report the first-attempt p99 next to it. See the open questions.
  - If clock skew exceeds about 1 second, measure the two halves separately.
- **Latency budget:** the relay poll, the broker, the consumer and the sender all count. Set the relay poll to about 1 second.
- **Data moves and state:** as in Step 7.
- **On failure:** if the gate fails, keep `order_confirmed` on the monolith and fix the latency. Do not start Step 9.

### Step 9. Cut over `password_reset`

- **Starts:** setting `notifications.owner.password_reset = service`, after the Step 8 gate has passed.
- **Does:** the same as Step 7. This is user-blocking, so watch the p99 closely.
- **Hold:** keep the old worker deployable for 7 days after this flip.
- **Rollback:** set the flag back to `monolith`. No row is re-owned.
- **On failure:** as in Step 7.

### Step 10. Decommission the old worker

- **Starts:** 7 days after `password_reset` has run on the service.
- **Preconditions:** all must hold, or do not remove the worker. Investigate first.
  - No `owner = monolith` rows are pending.
  - No shadow rows remain.
  - The reconciler reports no stuck rows.
  - All three types are owned by `service`.
- **Does:** remove the sender path in `run_worker` and `_deliver`. Remove the monolith's template import if nothing else uses it. Keep the outbox relay, the status consumer and the reconciler.
- **After this point:** rollback is a redeploy, not a flag flip. Say so in the change ticket.
- **Retention:** purge monolith outbox rows that are final and older than 30 days. The service's dedupe horizon is separate.

## Monitoring and risks

- **Dead service:** the service only pages on its own failures. The backlog-age and stuck-status alerts from Steps 4 and 5 must catch a fully dead service.
- **Template drift:** the service's template copy must match the monolith's during shadow and cutover. Freeze template edits for a type from Step 6 until Step 10, or version the templates.
- **Personal data:** the service stores email addresses. User deletion and retention need an owner and a propagation path from the monolith to the service.
- **Duplicate-send guarantee:** every send uses the notification id as its key, and the service dedupes by id. The residual risk is a send after MailRelay's 24-hour window. The resend guard narrows that risk.

## Open questions

1. What are the broker's retention and maximum redelivery horizon? This sets the inbox retention.
2. Is the 23-hour resend guard acceptable as a new policy, given that the brief says to keep retries exact?
3. Should the Step 8 latency gate include retries? The recommendation is yes, plus a first-attempt p99.
4. How much clock skew is there between the monolith and service hosts?
5. How long are email addresses kept in the service, and how does erasure propagate?
6. Does MailRelay's key window start at first acceptance? This is assumed, and the overview does not state it.