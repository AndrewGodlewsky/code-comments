# Plan: extract notifications into a Notification Service

## Summary

Today the monolith sends notifications itself. Business code calls `enqueue_notification(tx, ...)`, which inserts a `pending` row in the `notifications` table inside its own transaction. A worker thread on every monolith instance polls that table, renders the template, sends through MailRelay, and updates the row. It commits once per batch, so a crash can resend a batch. That causes about 30 duplicate emails a week.

We are moving sending into a separately deployed Notification Service with its own database, one notification type at a time. Callers do not change. The monolith still records every notification first. A relay then publishes service-owned rows to the broker, and the service sends them. The service reports the result back over the broker. Each row has one sender for its whole life, and every send carries the notification id as MailRelay's idempotency key.

## Terms

- **Owner.** A new column `notifications.owner`, either `'monolith'` or `'service'`. It says which side sends the row. It is set once, when the row is created.
- **Flag.** The per-type flag `notifications.via_service.<type>`, read with `flags.get`. A change reaches every monolith instance within 10 s. It decides the owner of new rows only.
- **Relay.** A monolith job that publishes service-owned rows to the broker and marks them published after the broker confirms storage.
- **Inbox.** The service table keyed by notification id. It removes duplicates and holds retry state (`status`, `attempts`, `next_attempt_at`).
- **Result outbox.** A service table of `sent` and `failed` events waiting to be published back.
- **Idempotency key.** The notification id, passed to MailRelay on every send. MailRelay drops a repeat of the same key for 24 hours and returns success.
- **Broker.** At-least-once. A message not acknowledged within 30 s is redelivered, possibly to another consumer.

## Rules for every step

- **Retries match today.** There are 5 attempts, with waits of 1, 2, 4 and 8 minutes before attempts 2 to 5. After that the row is marked `failed` and on-call is paged. The attempt counter goes up only when MailRelay returns an error. The service uses the same constants and logic.
- **No duplicate emails, by three layers.**
  1. The inbox primary key absorbs broker redelivery and relay republish.
  2. The idempotency key absorbs a crash after MailRelay accepts but before the local commit. Retries span at most 15 minutes and crash recovery takes seconds to minutes, so this is well inside the 24-hour window.
  3. Exclusive ownership means the monolith never sends a service-owned row.
- **Nothing lost.** Every row is committed in the monolith before anything else happens. Every later hop is retried until confirmed.

## How the system runs (once all types have moved)

| # | Part | Starts when | What it does | Where state lives | If it fails |
|---|------|-------------|--------------|-------------------|-------------|
| A | Intake | Business code calls `enqueue_notification` | Inserts a `pending` row with `owner` taken from the type's flag. A missing or failing flag means `'monolith'`. | Monolith `notifications` | The row exists only if the caller's transaction commits. Nothing is lost. |
| B | Relay | Polls every 1 s | Selects rows with `owner='service'` and no `published_at`, using `FOR UPDATE SKIP LOCKED`. Publishes `{id, type, user_id, email, payload, created_at}`, waits for the broker confirmation, then sets `published_at`. | Monolith `notifications` | A crash before `published_at` republishes the row, and the inbox removes the duplicate. If the broker is down, rows stay unpublished and the relay backs off. |
| C | Consumer | A broker message arrives | In one service-DB transaction, inserts into `inbox` (`status='pending'`, `attempts=0`, `next_attempt_at=now()`) with `ON CONFLICT (id) DO NOTHING`. Commits, then acknowledges. | Service `inbox` | A crash before the ack causes redelivery, which hits the conflict and is acknowledged. A message that keeps failing goes to a dead-letter queue and pages on-call. |
| D | Sender | A due `inbox` row exists | Claims one row with `FOR UPDATE SKIP LOCKED`, renders the template, and sends with `idempotency_key=id`. In the same transaction it records `sent`, the next retry, or `failed`. It commits per row. For `sent` and `failed` it also writes a `result_outbox` row. A `failed` row also records "page owed". | Service `inbox`, `result_outbox` | A crash mid-send releases the lock, and another instance re-sends with the same key. If MailRelay is down, the row follows the 1/2/4/8 minute backoff, then fails and pages. The page goes out after the commit and is then cleared. A crash can page twice but never zero times. |
| E | Result publisher | A `result_outbox` row exists | Publishes the event and marks it after the broker confirms. | Service `result_outbox` | At-least-once. Duplicates are harmless because of step F. |
| F | Result consumer | A result event arrives | Runs `UPDATE notifications SET status=..., attempts=... WHERE id=? AND status='pending'`, then acknowledges after commit. | Monolith `notifications` | A repeat does nothing. |

Rows with `owner='monolith'` keep using today's worker, with one change: it sends the idempotency key and only selects `owner='monolith'` rows.

## Rollout steps, in shipping order

1. **Send the idempotency key from the old worker.**
   - Starts when: this is the first change shipped.
   - Change: `_deliver` calls `mailrelay.send(..., idempotency_key=row.id)`.
   - Failure: after a crash, or a MailRelay timeout after accepting, the re-send uses the same key. MailRelay drops it and returns success, so the row is marked `sent` without a second email.
   - Gate: support's duplicate-email count stays near zero for a week. Rows re-sent before this shipped are not covered.

2. **Prepare the monolith.**
   - Starts when: step 1 is verified.
   - Migration: add `owner` (default `'monolith'`) and `published_at` (null).
   - Code: `run_worker` adds `AND owner = 'monolith'`. `enqueue_notification` reads the flag and writes `owner`. All flags are off, so every row is `'monolith'`.
   - Gate: before any flag is turned on, confirm that every monolith instance runs the filtered worker. An old-code worker would grab service-owned rows.
   - Failure: if instances disagree on a flag for up to 10 s, each row is still stamped once, so nothing is duplicated.

3. **Build and deploy the service in dark mode.**
   - Starts when: it can run in parallel with step 2. Nothing is published to it until step 6.
   - Builds: its own database, parts C, D and E above, template rendering moved from `templates.render`, and paging through `alerts`.
   - Failures: as in the table. If the broker is down, the consumer reconnects and unacknowledged messages are redelivered.

4. **Deploy the relay and result consumer, still inert.**
   - Starts when: steps 2 and 3 are deployed.
   - Builds: parts B and F above.
   - Alerts added: the oldest unpublished service-owned row is older than 30 s, and a published row has had no result for 30 minutes.
   - Failures: as in the table. Nothing is lost while the broker is down, because the row is in the committed monolith table.

5. **Rehearse failures and rollback with a synthetic type.**
   - Starts when: step 4 is deployed.
   - Method: a test-only type that goes to internal mailboxes and has its own flag.
   - Drills: kill the service mid-send, kill the relay mid-publish, force broker redelivery, take MailRelay down for more than 15 minutes (the row must end `failed` with a page), take the broker down, and flip the flag back and forth under load.
   - Pass: each notification produces exactly one email and one final status.

6. **Move `shipping_update` (40,000/day).**
   - Starts when: step 5 passes. Turn on `notifications.via_service.shipping_update`.
   - Effect: new rows get `owner='service'` and flow through parts B to F. Rows stamped `'monolith'` before the flip drain on the old worker.
   - Soak: at least 3 days. Watch duplicate complaints, rows with no result, dead-letter depth, unpublished age and enqueue-to-MailRelay latency.

7. **Move `order_confirmed` (12,000/day).**
   - Starts when: `shipping_update` has run on the service for at least 3 days and is clean.
   - Latency measurement: p99 of `accepted_at - created_at`. `created_at` travels in the message. `accepted_at` is the service's time when MailRelay accepted the send, returned in the result event. Both clocks must be on NTP, and we alarm if skew exceeds 1 s. The metric includes retried notifications, so a MailRelay failure rate above about 1% would breach 60 s. Today's policy has the same property.
   - Soak: at least 3 days.

8. **Move `password_reset` (1,500/day, p99 under 60 s).**
   - Starts when: `order_confirmed` has run on the service for at least 3 days, and its p99 enqueue-to-MailRelay latency over that period was under 60 s.
   - Added protection: an alert when the oldest unpublished `password_reset` row is older than 20 s, and a p99 dashboard with an alarm at 45 s.
   - Broker outage: reset emails queue in the table and go out when the broker recovers. On-call decides what to do after the alarm. The row is never moved back to the monolith, because that could duplicate the email.

9. **Decommission the old worker.**
   - Starts when: `password_reset` has run on the service for 7 days and all three flags have been on throughout.
   - Check first: no `owner='monolith'` rows have `status='pending'`.
   - Until then: the old worker stays deployed and idle, as the rollback path.
   - Change: remove `run_worker`, `_deliver` and the worker filter. Hard-code `owner='service'` in `enqueue_notification` and remove the flags. Keep the relay and the result consumer.
   - After this: rollback means redeploying the previous version. Per-type rollback by flag no longer exists.

## Rollback (steps 6 to 8)

Rollback is a flag flip that takes effect within about 10 s.

1. Turn the type's flag off.
2. New rows are stamped `'monolith'` and sent by the old worker.
3. Rows already stamped `'service'` stay with the service until they finish. The old worker's filter never touches them, so nothing is re-sent or lost.
4. Keep the relay and the result consumer running during a rollback.

The cost: if the service itself is down, in-flight service-owned rows wait for it to recover. They are not lost, and the alerts fire.

## What happens when things fail

| Failure | Result |
|---------|--------|
| Service crash mid-send | Another instance re-sends with the same key. MailRelay drops the repeat. |
| Relay crash after broker confirm | The row is republished. The inbox drops the repeat. |
| Broker redelivery | The inbox conflict is acknowledged. |
| Broker down | Rows wait in the monolith table. The relay and consumer reconnect. Alerts fire. |
| MailRelay down | Retries follow 1/2/4/8 minutes, then `failed` and a page. |
| Poison message | Dead-letter queue and a page. |
| Flag read fails | The row is stamped `'monolith'`. |
| Service down during rollback | In-flight rows wait. Nothing is re-sent. |

## Open risks

- **Rollback when the service is down.** In-flight rows wait for the service. They are not reclaimed, because the 24-hour idempotency window makes reclaiming unsafe if the service recovers late.
- **Clock skew.** It can distort the latency metric, so it is monitored.
