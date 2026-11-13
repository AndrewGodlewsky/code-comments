# Notification Service extraction plan

## Summary

Notifications become a transactional outbox inside the monolith. Business code is unchanged, and the existing `notifications` row stays the first record. A publisher hands committed rows to the broker. The Notification Service stores them in its own database, renders and sends them, and reports status back over the broker. Each type moves by a flag. Every MailRelay send is keyed by the notification id, so the same id is not accepted twice even when two senders overlap during a flag flip. Volume is small (about 53,500 notifications a day, under one per second on average), so the constraints that matter are the duplicate rules, the latency gate and the rollback rules, not throughput.

## Rules that hold in every step

1. **Enqueue is unchanged.** `enqueue_notification(tx, ...)` still inserts a `pending` row inside the caller's transaction. Only the row's later state changes. A rolled-back business transaction leaves no row, so nothing is published.
2. **The row is the outbox.** The publisher reads committed rows only, so there is no dual write between the database and the broker.
3. **Ownership comes from a status claim, not from the flag.** A sender claims a row by changing its status under a lease. A flag only decides which claimer runs for a type. Two claimers cannot hold the same row at once, except after a lease expires.
4. **Every MailRelay send carries `idempotency_key = notification id`.** This covers crashes, redelivery, mixed-version rollouts and ownership changes. The guarantee holds only inside MailRelay's 24-hour window, so every handoff, reclaim and retry must finish well inside it. Leases are minutes and the retry schedule totals 15 minutes. Decision D2 covers the remainder.
5. **The service acks a broker message only after its inbox row is committed.** The inbox insert is `INSERT ... ON CONFLICT (id) DO NOTHING`, so redelivery is harmless. A duplicate message also re-emits the row's current terminal status.
6. **The service never checks the flag.** It accepts every message it receives, so messages already in flight are not stranded when a type is rolled back.

## Monolith state (`notifications.status`)

| Status | Meaning | Held by | Next states |
|---|---|---|---|
| `pending` | committed, unclaimed | none | `sending` (monolith-routed) or `publishing` (service-routed) |
| `sending` | monolith sender holds a lease | monolith | `sent`, `failed`, or `pending` (retry) |
| `publishing` | publisher holds a lease | monolith | `handed_off`, or `pending` (broker error) |
| `handed_off` | broker confirmed; the service owns the row | service | `sent` or `failed` (from a status event) |
| `sent` | terminal | none | none |
| `failed` | terminal; on-call paged | none | none |

Expired `sending` or `publishing` leases are reclaimed by whichever claimer owns the type at that moment. `lease_until` and `handed_off_at` are added in step 1. The existing `attempts` and `next_attempt_at` keep their meaning.

## Steps

### Step 1. Expand the monolith schema

- **Starts:** the migration ships before any code that uses it.
- **Data moves:** none.
- **State:** monolith database. Add nullable `lease_until` and `handed_off_at`. Widen `status` to allow `sending`, `publishing` and `handed_off` if a CHECK constraint or enum exists. No backfill.
- **On failure:** the change is additive and nullable, so the current worker ignores it. Leave the columns in place if a rollback is needed.

### Step 2. Old worker: idempotency key and per-row claim

- **Starts:** deploy of the changed `run_worker`. No type moves yet.
- **Data moves:** MailRelay `send(..., idempotency_key=row.id)`.
- **Change:** in a short transaction, claim up to `BATCH_SIZE` pending rows by setting `status='sending'`, incrementing `attempts`, and setting `lease_until = now() + 5 min`. Call MailRelay outside any transaction. Commit each row's result separately. This replaces one commit per batch. Expired `sending` rows are reclaimed, and each reclaim counts as an attempt. The retry policy is unchanged: wait `BACKOFF_MINUTES[attempts-1]`, then mark `failed` and page on attempt 5.
- **State:** monolith database.
- **On failure:**
  - Crash after MailRelay accepted: the lease expires and the retry sends the same key, which MailRelay drops.
  - Crash before the call: one resend, no duplicate.
  - MailRelay timeout: handled as an error and retried with the same key.
  - Mixed versions during rollout: old and new instances can both send a row. The key makes that safe.
- **Gate:** staging shows MailRelay drops a second send with the same key. Support-reported duplicates fall.

### Step 3. Publisher and status consumer, routing still off

- **Starts:** deploy. Every `notif_route.<type>` flag is `monolith`.
- **Data moves:** none. The publisher claims only `pending` rows whose type routes to the service, so with all flags off it does nothing.
- **Broker:** create topic `notifications`, keyed by notification id, and consumer group `notif-service`. Retention is set by D1.
- **Messages:**
  - Enqueue message: `{v:1, id, type, user_id, email, payload, enqueued_at}`.
  - Status event: `{v:1, id, status, accepted_at | failed_at, last_error}`.
- **Publisher:** claims service-routed `pending` rows (`publishing`, 5-minute lease), publishes, waits for broker confirmation, then sets `handed_off` and `handed_off_at`. A broker error sets the row back to `pending` with a short delay.
- **Status consumer:** moves a `handed_off` row to `sent` or `failed`. It ignores rows in any other state, so it never moves a row backwards.
- **On failure:** if the publisher or broker is down, rows wait in `pending`. Nothing is lost and nothing is sent. Alert on the age of the oldest pending row.

### Step 4. Deploy the service with no traffic

- **Starts:** service CD. The service database is created with no grants to the monolith database, and the service holds no monolith credentials.
- **Contents:**
  - broker consumer;
  - `notifications` table in the service database, with the monolith's columns plus `status`, `attempts`, `next_attempt_at`, `lease_until`, `accepted_at` and `last_error`;
  - `status_outbox` table;
  - sender worker;
  - templates copied from the monolith;
  - MailRelay client that always sends `idempotency_key`;
  - metrics and alerts.
- **Data moves:** none yet.
- **On failure:** no traffic is flowing, so nothing is at risk. Dashboards and alerts must work before step 5.

### Step 5. Staging and fault-injection gate

- **Starts:** step 4, in staging against the MailRelay sandbox (D4).
- **Tests:**
  - Kill the sender after the MailRelay call and before commit. Expect one accepted send per id.
  - Deliver the same broker message three times. Expect one inbox row and a repeated status event.
  - Make MailRelay fail for 20 minutes. Expect retries at 1, 2, 4 and 8 minutes, then `failed` and one page.
  - Take the service down for 1 hour under load. Expect no loss after recovery.
  - Flip flags in both directions under load. Expect no id sent twice and none lost.
  - Roll back a business transaction. Expect no row and no message.
- **Pass:** every id reaches `sent` or `failed` exactly once, every failure produces one page, and the sandbox report shows no id accepted twice.

### Step 6. Cut over `shipping_update`

- **Starts:** set `notif_route.shipping_update = service`. Takes effect within 10 seconds.
- **Data flow:** monolith publisher hands off pending rows → broker (keyed by id) → service inbox insert, commit, ack → sender claims the row (`sending`, lease) → render templates → MailRelay with key → result written with a `status_outbox` row in the same transaction → status event → monolith sets `sent` or `failed`.
- **State:** monolith `notifications` (outbox and record); service `notifications` and `status_outbox`.
- **On failure:**
  - Publisher crashes after broker confirmation but before `handed_off`: the lease expires, the message is republished, and the inbox deduplicates it.
  - Broker down: rows wait in monolith `pending`. Nothing is lost. Alert on age.
  - Service down: the broker redelivers unacked messages after 30 seconds. On return, the inbox deduplicates.
  - MailRelay down: the service retries on the 1/2/4/8-minute schedule, then marks `failed` and pages. Only the service pages for this row.
  - Render error: counted as a failed attempt, so it cannot loop.
- **Soak:** at least 3 days. Exit when reconciliation (Verification) is clean, the failure rate is at or below the pre-cutover baseline, and backlog age p99 is under 60 seconds.

### Step 7. Cut over `order_confirmed`

- **Starts:** step 6 exit. Set `notif_route.order_confirmed = service`.
- **Mechanics:** as step 6.
- **Latency measurement:** enqueue-to-accept per row is the service `accepted_at` minus the monolith `enqueued_at` (D5). Record p99 per day and across the full soak.
- **Soak:** at least 3 days. Exit when p99 is under 60 seconds across the full soak and no single day exceeds 60 seconds. This is the gate for step 8.
- **On failure:** as step 6. A broker outage longer than about 60 seconds breaches this SLO by design. Handle it under D8.

### Step 8. Cut over `password_reset`

- **Starts:** step 7 latency gate passed. Set `notif_route.password_reset = service`.
- **Mechanics:** as step 6, with the latency alarm applied to this type.
- **Soak:** at least 7 days.
- **Old worker:** stays deployed and idle for the whole soak. It is the rollback sender for all three types.
- **On failure:** roll back per the procedure below.

### Step 9. Decommission the old worker

- **Starts:** 7 days after step 8 completes, with no rollback open.
- **Removes:** `run_worker`, the monolith sender branch, the `notif_route` flags, and the monolith copies of the templates.
- **Keeps:** `enqueue_notification`, the publisher and the status consumer. The monolith `notifications` table remains the record.
- **On failure:** a rollback after this point means reinstating a sender (D7).

## Rollback (any type, at any time)

1. Set `notif_route.<type> = monolith`. Within 10 seconds the publisher stops claiming that type, and the monolith sender starts claiming its `pending` rows.
2. Rows already `handed_off` stay with the service, which keeps consuming and sending them. Do not stop the service consumer or sender until its inbox for the type is empty.
3. Expired `publishing` leases for the type are reclaimed by the monolith sender. The broker may already have confirmed some of these, so the same id can reach both senders. The key covers this only inside the 24-hour window, and the short lease keeps the overlap to minutes.
4. In the normal case nothing is re-sent. The monolith never resends a `handed_off` row, and the service does not send a row it has already marked `sent`.
5. Confirm that the `pending` count for the type reaches zero, the service inbox for the type drains, and reconciliation is clean.

## Verification (run daily during every cutover)

- **No loss:** every committed `notifications` row older than the maximum retry window (about 1 hour) is `sent` or `failed`. Any other row pages on-call.
- **Stalled handoffs:** a `handed_off` row with no status after 1 hour is republished. The inbox deduplicates it, and the service re-emits the status.
- **No duplicates:** compare the service's accepted-send log with the monolith record. Any id with more than one accepted send pages on-call.
- **One page per failure:** each `failed` row has exactly one page, raised by the owner at the time of failure.

## Decisions needed

- **D1. Broker retention.** The overview does not state retention. It must cover the longest outage we will tolerate. I suggest at least 72 hours. Confirm with the billing and search owners, who share the broker.
- **D2. MailRelay 24-hour window.** No duplicate is guaranteed if an attempt is re-sent more than about 20 hours after its first send. Retries and reclaims finish within an hour, but a service that is down for a day can hold an accepted-but-unrecorded attempt. Proposal: the sender stops resending any row whose ambiguous attempt is older than 20 hours and pages on-call for manual reconciliation. The tradeoff is that a notification that was actually sent may be marked `failed`, but it will not be sent twice.
- **D3. PII on the broker.** Email addresses and payloads cross the broker and are stored in the service database. Confirm topic ACLs, encryption at rest and retention. The service cannot read the monolith database, so it cannot look up the email instead.
- **D4. MailRelay sandbox.** Confirm that the sandbox honours `idempotency_key` and whether MailRelay can report accepted sends by key. Without that, step 5 and the duplicate check cannot produce proof.
- **D5. Latency clocks.** Enqueue time comes from the monolith database clock and accept time from the service clock. Assume NTP skew under 1 second, and state that assumption on the latency dashboard.
- **D6. Template ownership.** Templates exist in both places from step 4. Freeze template edits for the three types until step 9, or ship each edit to both copies in the same release.
- **D7. Keep a sender after decommission?** The brief removes the old worker 7 days after `password_reset` moves. Rolling back after that means reinstating a sender. The alternative is to keep the sender code behind the flag indefinitely.
- **D8. Automatic fallback.** The plan has no automatic fallback to the monolith when the broker or service is unhealthy, and flags are changed manually. Automatic fallback would be safe in principle because the key covers overlap, but it would mask breaches of the 60-second `password_reset` SLO, including those caused by a broker outage.