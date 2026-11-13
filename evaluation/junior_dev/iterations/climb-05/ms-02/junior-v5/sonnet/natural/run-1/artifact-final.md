# Plan: extract notifications into a Notification Service

## Summary

**Today.** Business code (checkout, carrier webhook, password reset) calls `enqueue_notification(tx, ...)`, where `tx` is its own database transaction. The call inserts a row into the monolith's `notifications` table with status `pending`. The row exists only if that transaction commits. A worker thread on every monolith instance polls every 5 s. It claims up to 50 due `pending` rows with `FOR UPDATE SKIP LOCKED`, renders and sends each through MailRelay (our email provider), and commits once per batch. A failed send adds 1 to `attempts` and sets `next_attempt_at` to 1, 2, 4 or 8 minutes ahead. The 5th failure marks the row `failed` and pages on-call. Two problems: a crash after MailRelay accepts part of a batch but before the commit sends those emails again (about 30 duplicates a week), and sending competes with checkout for CPU and database connections.

**The change.** Callers and the first write stay the same. Only sending moves to a separately deployed Notification Service with its own database. The two sides talk only through the message broker. A monolith component called the dispatcher publishes each `pending` row to the broker. The service sends the email, retries, and publishes the outcome back. A per-type flag decides which side sends, so types move one at a time and can move back. Safety against loss comes from keeping the monolith row until the broker confirms the handoff, and from reconciling later. Safety against duplicates comes from deduplicating on `id` in the service and passing `id` to MailRelay as `idempotency_key` on every send.

## Terms

- **Broker**: the existing message broker that billing and search already use. It is at-least-once. A message not acknowledged (acked) within 30 s is redelivered, possibly to another consumer. A publisher gets a *storage confirmation* once the broker has stored its message. This plan uses two topics: `notification.requested` (monolith to service) and `notification.outcome` (service to monolith).
- **MailRelay `idempotency_key`**: if MailRelay accepted a send with the same key in the last 24 h, it drops the new send and returns success. We pass the notification `id` as the key.
- **Route flag**: one per type, `notifications.route.<type>`, value `monolith` (default) or `service`. It says which side may send that type. It is read with `flags.get`, the monolith's runtime flag lookup. A change reaches every monolith instance within 10 s.
- **Monolith status**: `pending` (recorded, not yet handed on), `handed_off` (new: the broker confirmed storing the handoff, so the service owns delivery), `sent`, `failed`.
- **Service status**: `received`, `sent`, `failed`. Each service row also has `attempts`, `next_attempt_at` and `lease_until`.
- **Due**: a service row is due when it is `received`, `next_attempt_at <= now()`, and `lease_until` is empty or past.
- **Lease**: a short claim (2 min) on a row by one sender, so two senders do not send the same row at once.
- **Outbox**: a service table of outcome events waiting to be published. Writing the event in the same commit as the status change means no outcome is forgotten.

## How it runs

Components. Monolith: the **dispatcher**, the **outcome consumer** and the **reconciler**. Service: a **consumer**, a **sender**, an **outbox publisher** and a **pager**. The service DB holds a `notifications` table (`id` primary key, `type`, `user_id`, `email`, `payload`, `created_at`, status, `attempts`, `next_attempt_at`, `lease_until`, `paged`) and the `outbox` table (each event has a `published_at`, empty until published). Templates move into the service.

1. **Record.** Business code calls `enqueue_notification` as today. State: the monolith `notifications` table.
   - If the transaction rolls back, there is no row and no notification, as today.
2. **Dispatch** (monolith, every 1 s, only for types whose flag is `service`).
   - In a short transaction, select up to 50 due `pending` rows of those types with `FOR UPDATE SKIP LOCKED`.
   - Publish one message per row with `id`, `type`, `user_id`, `email`, `payload`, `created_at`, `attempts` and `next_attempt_at`. Wait for the storage confirmation. The publish phase has a 10 s limit. If it is exceeded, roll back and retry next second, so a slow broker cannot hold row locks for long.
   - Set `handed_off` and `handed_off_at`, then commit.
   - If the broker is down or the dispatcher crashes before the commit, the rows stay `pending` and are published again. Nothing is lost, and this does not use up send attempts.
3. **Receive** (service consumer).
   - Insert the row with `INSERT ... ON CONFLICT (id) DO NOTHING`, status `received`. The message's `attempts` and `next_attempt_at` are used on first insert, so a row the old worker already tried keeps its retry budget. For an existing row they are ignored: the service owns them from the first handoff.
   - If the row exists and is terminal, write its outcome event to the outbox again. If it exists and is `received`, do nothing, because it is already durable and the sender owns it.
   - Commit, then ack. This holds in every case, so a redelivered handoff is a no-op.
4. **Send** (service sender, every 1 s).
   - Claim a due row: set `lease_until = now() + 2 min` and commit. No transaction stays open during the send.
   - Render the template and call MailRelay with `idempotency_key = id`.
   - On success, in one commit: set `sent`, clear the lease, write the outbox event.
   - On `mailrelay.Error` (including timeouts and render failures): add 1 to `attempts` and clear the lease. If `attempts < 5`, set `next_attempt_at` to now plus 1, 2, 4 or 8 minutes (the same policy as today). If `attempts >= 5`, in one commit set `failed`, `paged=false` and write the outbox event.
   - A due row with an expired lease means a sender crashed mid-send. It is simply sent again, and the crash does not count as an attempt. If MailRelay had accepted the first send, the key makes it drop the second.
5. **Page** (service pager, every 10 s). Select `failed` rows with `paged=false`, call `alerts.page_oncall`, then set `paged=true`. A crash in between repeats the page, which is acceptable.
6. **Publish outcome** (service outbox publisher, every 1 s). Read outbox rows with empty `published_at`, publish each to `notification.outcome`, wait for the storage confirmation, then set `published_at`. A crash in between publishes the event twice, which is safe. The event holds `id`, final status and `attempts`. The failure reason stays in the service and in the page.
7. **Apply outcome** (monolith outcome consumer). Run `UPDATE notifications SET status = :s WHERE id = :id AND status = 'handed_off'`, commit, then ack. If the row is not `handed_off`, nothing changes and the event is acked, so repeats are harmless. If the row is still `pending` because the dispatcher has not committed yet, step 8 repairs it: the row is republished, the service re-emits the outcome, and it then applies.
8. **Reconcile** (monolith, every 5 min). Republish any row that has been `handed_off` for over 30 min (twice the 15 min retry window). The service ignores it if the row is still `received` and backing off, and re-emits the outcome if it is terminal. This repairs lost or late outcome events. Alert if a row is still `handed_off` after 1 h.

**Honest limit.** The key only protects within 24 h. The alert on any in-flight notification older than 1 h means a human acts long before that.

## What happens when things fail

| failure | what happens |
|---|---|
| Caller's transaction rolls back | No row, no notification. |
| Broker down at dispatch | Publish fails, transaction rolls back, rows stay `pending`. Alert if the oldest service-routed `pending` row is older than 2 min (30 s for `password_reset`). First remedy: flip that type to `monolith`, which sends the backlog. |
| Broker down at the service | The consumer waits and retries. Outbox events accumulate and drain later. |
| Dispatcher crashes after publish, before commit | Row stays `pending` and is published again. The service dedupes on `id`. |
| Handoff redelivered | `ON CONFLICT` makes it a no-op. |
| Poison message (undecodable, or redelivered over 10 times) | Goes to a dead-letter queue and pages on-call. The monolith row stays `handed_off`. The reconciler's republish after 30 min is a fresh try, and the 1 h alert fires if it is still stuck. |
| Service crashes mid-send | The lease expires, the row is sent again, MailRelay drops it by key, and the sender records `sent`. |
| MailRelay down or erroring | The normal retry policy applies, ending in `failed` and a page. The pager repeats until `paged=true`. |
| Service DB down | The consumer cannot commit, so it does not ack and the broker redelivers. |
| Outcome event lost or late | The reconciler repairs it. |
| Monolith DB down | Nothing works, and enqueueing fails as today. |

Service alerts that page on-call (thresholds are our choice, not requirements): service DB unreachable, oldest unpublished outbox row older than 2 min, oldest due `received` row due for over 5 min, dead-letter queue not empty.

## How we roll it out

Rollback for any type is the same: set its flag back to `monolith`. The dispatcher stops claiming the type and the old worker claims new `pending` rows, within about 10 s plus one poll. Rows already `handed_off` stay in the service until they finish and report back, so none are lost and none are re-sent. The service keeps running whatever the flag says. If the flag is flipped while a dispatcher publish is uncommitted, the old worker may also send that row, and the shared key makes MailRelay drop the second send.

1. **Pass `idempotency_key` on the old worker.** Starts now, as an ordinary monolith release. Change `_deliver` to call `mailrelay.send(..., idempotency_key=row.id)`. No schema change. After this, a crash that re-sends a batch is dropped by MailRelay, which fixes the weekly duplicates, and a timeout that actually delivered is not delivered twice on retry. Done when one release cycle passes with no new duplicate reports. Every later step depends on it, because both senders must share the key.
2. **Make the old worker route-aware, all flags `monolith`.** Starts when step 1 is live. A migration adds the `handed_off` status and the `handed_off_at` column. Create the three flags set to `monolith`. The worker's claim query gains `AND type = ANY(<types whose flag is 'monolith'>)`, reading the flag at the start of each batch. If the flag read fails, default to `monolith`, so behaviour is as today. Done when all instances run it, before any dispatcher exists, so an old-code instance cannot claim rows meant for the service.
3. **Deploy the Notification Service with no traffic.** Can run in parallel with steps 1 and 2, but must be live before step 4 is enabled. It includes the service DB, consumer, sender, outbox publisher, pager, templates and alerts described above.
4. **Add the dispatcher, outcome consumer and reconciler to the monolith.** Starts when steps 2 and 3 are done. All flags are still `monolith`, so the dispatcher finds nothing. Dispatcher polling at 1 s, faster than the old worker's 5 s, gives the 60 s `password_reset` target margin.
5. **Verify in staging, then in production with flags at `monolith`.** Staging uses the MailRelay sandbox. A one-off monolith job writes sanitised sample payloads to a fixture file, because the service never reads the monolith DB. Checks, and any failure blocks step 6:
   - Rendering parity: monolith and service templates give identical output for all three types.
   - Chaos tests, each asserting exactly one accepted email per id: kill the consumer mid-handoff; kill the sender between MailRelay accept and commit; force broker redelivery; take the broker down while the dispatcher runs; make MailRelay fail all 5 attempts and check the 1/2/4/8 min timing, the `failed` status and the page; kill the dispatcher after publish and before commit.
   - Rollback drill: under load, flip a flag back and forth, including mid-batch, and assert no loss and no duplicate.
   - Flag timing: flip-to-effect is under 60 s.
6. **Cut over `shipping_update`** (40,000 a day, no latency requirement). Starts when step 5 passes. Set its flag to `service`. New rows are dispatched. Existing `pending` rows, including ones the old worker already tried, are dispatched with their `attempts` and `next_attempt_at`, so the total budget stays 5. Rows the old worker has locked mid-batch finish there, since `SKIP LOCKED` keeps the dispatcher off them. Watch for at least 3 days. Move on only if there are no duplicate reports, no `handed_off` row older than 30 min, an empty dead-letter queue, a failure rate no worse than before, and latency recorded (`created_at` to MailRelay accept, p50 and p99).
7. **Cut over `order_confirmed`** (12,000 a day). Starts when step 6 has run 3 days and its criteria hold. Same mechanics as step 6. Also confirm checkout CPU and database connection use dropped. Watch for at least 3 days. Record p99 enqueue-to-MailRelay latency for all sends and separately for first-attempt successes.
8. **Latency gate.** Starts when `order_confirmed` has run 3 days. Passes if p99 `created_at` to MailRelay accept on `order_confirmed` is under 60 s over the whole window, with NTP-synced clocks. If missed, tune dispatcher poll, sender concurrency and batch size, then measure a fresh window. `password_reset` stays on the monolith until it passes. This step only reads metrics.
9. **Cut over `password_reset`** (1,500 a day, p99 under 60 s). Starts when step 8 passes. Same mechanics as step 6. Also page if the oldest service-routed `password_reset` `pending` row is older than 30 s, or if the p99 over the last hour exceeds 60 s. The first response to either is the flag flip. Watch for 7 days.
10. **Decommission the old worker.** Starts when `password_reset` has run 7 days, all flags are `service` and the criteria hold. Confirm no monolith-routed `pending` rows remain and no old-code instances run. Release a monolith version that removes `run_worker`, `_deliver` and the monolith templates. Keep `enqueue_notification`, the dispatcher, the outcome consumer and the reconciler. After a further clean release cycle, remove the route flags. Once the worker is gone, flag-flip rollback no longer exists and recovery means redeploying the old release, which is why the worker stays deployable for these 7 days.

| day | event |
|---|---|
| 0 | `shipping_update` moves |
| 3 or later | `order_confirmed` moves |
| 6 or later | latency gate checked, then `password_reset` moves |
| 13 or later | old worker removed |

## Open questions

- Where flag values are stored, and who changes them with which tool, is not in the existing files. Confirm that on-call can flip one within the one-minute rollback target.
- Who owns and clears the dead-letter queue, and how a dead-lettered message is replayed, is not described. The plan assumes on-call inspects it by hand.
