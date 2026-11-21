# Plan: extract notifications into a Notification Service

## What this is

Today the monolith records a notification in its `notifications` table, inside the caller's own transaction. A background worker on every monolith instance then renders the email and sends it through MailRelay, in batches. That worker competes with checkout for CPU and database connections. It also causes about 30 duplicate emails a week: if an instance dies after MailRelay accepts some of a batch but before the batch commit, those rows stay `pending` and are sent again.

We move sending into a separately deployed Notification Service with its own database. The flow is:

1. Business code records a row in the monolith, as it does today.
2. A new dispatcher in the monolith publishes that row to the message broker.
3. The service stores it, renders it, and sends it to MailRelay.
4. The service publishes the outcome, and the monolith writes it back onto its row.

The plan is shaped around three rules. The monolith row stays the first record and the final record. Every send carries the notification id as MailRelay's `idempotency_key`, so any repeated send is harmless. Who owns a row is decided by the row's `status` column, never by a flag, which keeps rollback safe.

## Terms

- **Monolith**: the existing application. It owns the `notifications` table.
- **Notification Service**: the new deployment. It owns its own database and never touches the monolith's database. The monolith never touches the service's.
- **Broker**: the shared message system, already used by billing and search. It is at-least-once. A message not acknowledged within 30 s is redelivered, possibly to another consumer. A publisher gets a confirmation once the message is stored.
- **MailRelay**: the email provider. If it has accepted a send with the same `idempotency_key` in the last 24 hours, it drops the new send and returns success.
- **Idempotency key**: the notification's id, passed on every send.
- **Status**: the monolith column that moves `pending` -> `handed_off` -> `sent` or `failed`. `handed_off` means the broker confirmed it holds the request and the service now owns the send.
- **Routing flag**: `notif.route.<type>` is `monolith` (default) or `service`. A change reaches every monolith instance within 10 s. It only decides what happens to rows that are still `pending`.
- **Dispatcher**: new monolith loop that publishes `pending` rows of service-routed types to the broker.
- **Old worker**: today's `run_worker` and `_deliver`.
- **Lease**: a 60 s claim on a service row, so two service instances do not normally send the same row at once.
- **Types**: `shipping_update` (about 40,000 a day), `order_confirmed` (12,000), `password_reset` (1,500; its p99 enqueue-to-MailRelay latency must stay under 60 s).

## How it runs

### Messages

- `notification.requested` (monolith -> service): `id, type, user_id, email, payload, attempts, next_attempt_at, created_at`.
- `notification.result` (service -> monolith): `id, status (sent|failed), attempts, finished_at`.

### Where state lives

| State | Owner |
|---|---|
| The notification exists | Monolith `notifications` row, written in the caller's transaction |
| Handed off or not | Monolith `status` |
| Attempts, backoff, lease, sent or failed, result published, paged (for handed-off rows) | Service database |
| Final outcome | Written back to the monolith row by the result consumer |
| Routing per type | Monolith flag |

The service table is `notifications(id PK, type, email, payload, attempts, next_attempt_at, created_at, status pending|sent|failed, lease_until, result_published_at, paged_at)`.

### Steps

1. **Record.** Business code calls `enqueue_notification(tx, ...)` inside its transaction. This does not change. The row is `pending`. If the caller's transaction rolls back, there is no row and no notification, as today.

2. **Pick the path.** A `pending` row of a `monolith`-routed type is sent by the old worker. A `pending` row of a `service`-routed type is picked up by the dispatcher. The old worker's query skips service-routed types, reading the flags on each loop. Both use `FOR UPDATE SKIP LOCKED`, so one claim wins.

3. **Hand off (dispatcher).** Runs every 1 s on each monolith instance.
   1. In one transaction, select up to 100 `pending` rows of service-routed types, oldest first, with `SKIP LOCKED`.
   2. Publish each as `notification.requested`, including its current `attempts` and `next_attempt_at`, so a row that already used attempts on the old worker keeps its count.
   3. Wait for the broker confirmations.
   4. Set `status = 'handed_off'`, then commit.
   - If it crashes before the confirmation, the lock is released and the row is still `pending`, so the next run republishes it. If it crashes after the confirmation but before the commit, the row is republished and the service ignores the duplicate.
   - If the broker is down, rows stay `pending` and nothing is lost. An alert fires when the oldest `pending` row of a service-routed type is older than 30 s. The runbook is to flip that type back to `monolith`. The old worker then sends those rows with the key.

4. **Store (service consumer).** On a `notification.requested` message, insert the row with `ON CONFLICT (id) DO NOTHING`, commit, then acknowledge. Then wake the sender so it does not wait for a poll. If the row is already `sent` or `failed`, re-emit its result instead of sending. If the broker redelivers, the insert is a no-op.

5. **Send (service sender).**
   1. Claim one due row: `status = 'pending'`, `next_attempt_at <= now()`, lease expired, with `SKIP LOCKED`. Set the lease to now plus 60 s.
   2. Render the template (rendering now lives in the service). Call `mailrelay.send(..., idempotency_key=id)`.
   3. Commit that one row immediately, not a whole batch:
      - Success: `sent`.
      - Error or timeout before attempt 5: add one to `attempts` and set `next_attempt_at` to now plus 1, 2, 4 or 8 minutes.
      - Error or timeout on attempt 5: `failed`.
   - This is today's retry policy exactly: 5 attempts, waits of 1/2/4/8 minutes, then failed and a page.
   - If the service crashes after MailRelay accepts but before the commit, the lease expires, another instance sends again, and MailRelay drops it because the key matches. A slow send that outlives its lease is handled the same way.
   - If MailRelay is down, the retry schedule runs, and after about 15 minutes the rows fail and are paged, as today.

6. **Report back.**
   - A result publisher scans terminal service rows with `result_published_at` empty, publishes `notification.result`, waits for the broker confirmation, then sets `result_published_at`. If the broker is down, results wait in the service database and publish on recovery. Sending continues meanwhile.
   - A pager pages on-call for `failed` rows with `paged_at` empty, then sets `paged_at`.
   - The monolith result consumer applies each result with `UPDATE ... SET status, attempts WHERE id = ? AND status <> 'sent'`, commits, then acknowledges. It is safe to repeat. A `sent` result may overwrite `failed`. That split case is rare, on-call was already paged, and the runbook says to reconcile by hand.

7. **Reconcile.** Every 15 minutes, a monolith job republishes `notification.requested` for rows that have been `handed_off` for over 1 hour. The service ignores it if the row is in progress and re-emits the result if it is finished. Alert if a row is still `handed_off` after 2 hours.

### Why a user never gets the same email twice

Each crash case ends in a repeated send with the same key: a crash after MailRelay accepts, a broker redelivery, a dispatcher crash after publishing, or a stale flag. MailRelay drops a repeated key for 24 hours, and the longest retry chain is 15 minutes. Repeated broker messages are also dropped by id in the service database.

### What happens when things fail

| Failure | Result |
|---|---|
| Caller's transaction rolls back | No row, no notification |
| Dispatcher crashes before or after the broker confirms | Row republished; service dedupes by id |
| Broker down | Monolith rows stay `pending`; service results queue; nothing lost |
| Broker redelivers a request | Insert is a no-op |
| Service crashes mid-send | Lease expires; resend with the same key; MailRelay drops it |
| MailRelay down | Today's retry schedule, then `failed` and a page |
| Stale flag on one instance (up to 10 s) | May hand off a row; the status column decides ownership, so it is sent once |
| Result lost or late | Reconciler republishes; alert after 2 hours |

## How we ship it

Each step ships only after the one before it is healthy.

1. **Pass the key on the old worker.** Change `_deliver` to call `mailrelay.send(..., idempotency_key=row.id)`. A crash-and-resend, or a timeout where MailRelay actually accepted, is now dropped for 24 hours. Check that the weekly duplicate count falls to about zero and that every instance runs this version before anything else moves.
2. **Monolith groundwork, no behavior change.** Add the `handed_off` status and a `handed_off_at` column, an index on `(status, type, created_at)`, the three flags set to `monolith`, and the type filter on the old worker's query. An old-version worker without the filter is still correct while all flags are `monolith`. Put every instance on this version before flipping any flag.
3. **Deploy the service with no traffic.** Build steps 4 to 6 of the run section and subscribe to `notification.requested`. Test in staging with a fake MailRelay that dedupes keys. Check that rendering is byte-equal to the monolith templates for golden payloads of all three types. Kill the service mid-send. Redeliver messages. Run a MailRelay outage and confirm the retry timing and the page.
4. **Deploy the dispatcher, result consumer and reconciler in the monolith.** They do nothing while all flags are `monolith`.
5. **Move `shipping_update` (day 0).** Set its flag to `service`. New rows and rows mid-retry are handed off with their `attempts` and `next_attempt_at`. After about 1 hour, run a rollback drill: flip back, confirm new rows go through the old worker and rows already handed off finish on the service with no double email, then flip forward. Soak for at least 3 days. Watch send success rate, the `handed_off` backlog, duplicate emails (expect 0), pages, and the age of the oldest `pending` row.
6. **Move `order_confirmed` (earliest day 3).** Start after `shipping_update` has run 3 days with no open incidents. The service records latency for each notification, from `created_at` in the message to the time MailRelay accepts it, and reports a rolling p99. This needs synchronized clocks on both sides. Soak for at least 3 days.
7. **Move `password_reset` (earliest day 6).** Start only if `order_confirmed` has run 3 days and its p99 stayed under 60 s. Otherwise fix the cause first. Alert if the oldest `pending` row is older than 30 s or the p99 goes over 60 s, and flip back at once if either fires.
8. **Remove the old worker (earliest day 13).** Start after `password_reset` has run 7 days on the service and no `pending` rows remain beyond the normal in-flight tail. Remove `run_worker`, `_deliver`, the `monolith` branch of the filter and the monolith template code. Keep `enqueue_notification`, the dispatcher, the result consumer and the reconciler. The flags are no longer a rollback route. If removal causes trouble, redeploy the previous build.

Rolling a type back restarts its soak clock and delays the types after it.

### Rollback (any type, any time before step 8)

1. Set `notif.route.<type> = monolith`. It takes effect within 10 s.
2. New rows stay `pending`, and the old worker sends them with the key.
3. Rows already `handed_off` are not touched. The service keeps retrying them and publishes results, and the monolith records them. Nothing is re-sent, because the monolith never sends a `handed_off` row.
4. Keep the service and its consumers running until that type's `handed_off` backlog is zero (about 15 minutes plus the broker window at most).

### Timeline

| Day | Event |
|---|---|
| 0 | Steps 1 to 4, then `shipping_update` moves |
| 3 earliest | `order_confirmed` moves |
| 6 earliest | `password_reset` moves, if p99 < 60 s on `order_confirmed` |
| 13 earliest | Old worker removed |

## Open questions and residual risks

- **MailRelay's 24 h key window.** If the service is down for over a day after MailRelay accepted a send but before the commit, a resend could get through. Mitigation: alert when the service backlog is older than 12 h.
- **Personal data on the broker.** `email` and `payload` travel in messages. The broker is shared with billing and search, so apply the same access controls.
- **Clock skew.** The latency measure compares timestamps from two systems. Keep NTP healthy and alarm on skew.
- **`sent` overriding `failed`.** When the old worker and the service disagree, it needs manual reconciliation after the page.
