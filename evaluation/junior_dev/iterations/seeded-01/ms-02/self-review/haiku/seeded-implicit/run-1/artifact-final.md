# Plan: extract notifications into a Notification Service

Today, the monolith (the main application) sends notification emails from a background thread inside its own process. That thread competes with checkout for CPU and database connections. We are moving the sending into a separate Notification Service that has its own database. Business code does not change. It still records a notification inside its own database transaction, and the monolith's `notifications` table stays the first place each notification is written.

## Terms

- **Notification**: one email to one user. Each has a UUID `id`.
- **Enqueue**: business code calls `enqueue_notification(tx, ...)` inside its own database transaction `tx`. The notification row exists only if that transaction commits. If the transaction rolls back, there is no notification.
- **Broker**: the message queue that billing and search already use. It is at-least-once, which means a message may arrive more than once. If a consumer does not acknowledge a message (confirm that it received it) within 30 s, the broker sends the message again, possibly to a different consumer. A publisher gets a confirmation once the broker has stored the message.
- **MailRelay**: the email provider. Its `send()` takes an `idempotency_key`. If MailRelay already accepted a send with that key in the last 24 hours, it ignores the new send and reports success. Sending again with the same key is therefore safe within that 24-hour window.
- **Route**: which side sends a notification, `monolith` or `service`. It is written to the row once, at enqueue time, and never changed.
- **Flag**: a runtime switch read with `flags.get(name)`. A change reaches every monolith instance within about 10 s.
- **Outbox**: a table of rows waiting to be published to the broker. For service-routed notifications, the monolith's `notifications` table plays this role.
- **Lease**: a time-limited claim on a row. A sender holds the row until `lease_until`. If the sender dies, the lease expires and another sender can claim the row.
- **Forward-only update**: a row's status moves from `pending` to `sent` or `failed`, and never changes after that. A repeated message therefore does nothing.
- **Retry policy** (unchanged, used on both sides): up to 5 send attempts. Wait 1, 2, 4 and 8 minutes before attempts 2 to 5. If attempt 5 fails, mark the notification `failed` and page on-call.

## Plan

The steps are in the order we would ship them. Each step says what starts it, what data moves, where the state lives, and what happens when something fails.

### 1. Send MailRelay idempotency keys from the existing worker

- **Starts when:** the updated monolith worker is deployed. No flag is involved.
- **Data moves:** the notification `id` is passed as `idempotency_key` on every `send()`.
- **State lives:** unchanged, in the monolith `notifications` table.
- **If something fails:** if the worker dies after MailRelay accepts a send but before its batch commit, those rows stay `pending` and are sent again with the same key. MailRelay drops the repeat, as long as it happens within 24 hours of the first send. This should remove the duplicates caused by crashes (about 30 a week). The retry policy is unchanged.

### 2. Stamp a route on every notification and add per-type route flags

- **Starts when:** the migration and the enqueue change are deployed. All route flags are unset, which means `monolith`. Traffic does not change.
- **Data moves:** nothing crosses a system boundary. Inside the caller's transaction, `enqueue_notification` reads `flags.get("notify.route.<type>")` and writes the result to a new `route` column on the row.
- **State lives:** a new `route` column on the monolith `notifications` table, with default `monolith`. The flags live in the flag store.
- **If something fails:** if the flag store cannot be read, the row gets `monolith`, which is today's path. The enqueue still succeeds. The monolith worker sends only `route = 'monolith'` rows, so existing traffic does not change.

### 3. Build the Notification Service, with no traffic

- **Starts when:** the service is deployed. It stays idle until step 4 starts publishing to it.
- **Data moves:** the service receives `{id, type, email, payload}` messages from the `notifications.requested` topic. It renders the email, sends it through MailRelay, and publishes each final result (`accepted` or `failed`) to `notifications.outcome`.
- **State lives:** only in the service's own database. The service never reads or writes the monolith database. Its main table is `deliveries`, with one row per notification, keyed by `id`. Each row holds the status (`received`, `sending`, `accepted` or `failed`), `attempts`, `next_attempt_at`, `lease_until`, the first and last send times, and the rendered message.
- **Parts:**
  - **Consumer:** for each message, runs one database transaction that inserts a `deliveries` row with status `received`. If a row with that `id` already exists, the insert does nothing. The consumer acknowledges the message only after that transaction commits. Retries are driven by `deliveries` rows, not by holding the message, so the 30 s acknowledgement window is never at risk.
  - **Sender:** a loop that claims due rows, meaning rows where `next_attempt_at` has passed and no unexpired lease exists. It claims them with `FOR UPDATE SKIP LOCKED`, a database instruction that skips any row another worker has already locked. It sets a lease, renders the template, calls `send()` with `idempotency_key = id`, and records the result or the next retry time.
  - **Templates:** copied from the monolith. For each type, a golden test (a test that compares output with a saved expected result) checks that the service renders the same subject and body as the monolith for the same payload.
- **If something fails:**
  - Crash after the insert but before acknowledgement: the broker redelivers the message, and the insert is ignored as a duplicate.
  - Crash during a send: the lease expires and another sender sends again with the same key. If the first send was accepted, MailRelay drops the repeat.
  - A row whose last send started more than 24 hours ago, with no recorded result: do not send it again, because the key window has passed. Mark it `failed` and page on-call so a person can check it.
  - MailRelay down or timing out: the normal retry policy applies, using `next_attempt_at`. After attempt 5, mark `failed` and page on-call.
  - Broker down: the consumer receives nothing, and messages wait on the broker. Nothing is lost.

### 4. Add the outbox relay and the outcome consumer to the monolith

- **Starts when:** a background loop on each monolith instance, written in the same style as today's worker, is deployed. It runs from this step on. Nothing is routed to the service until a flag changes in step 5.
- **Data moves:**
  - **Relay:** reads rows with `route = 'service'` and no `handed_off_at`, publishes `{id, type, email, payload}` to `notifications.requested`, and sets `handed_off_at` only after the broker confirms it has stored the message.
  - **Outcome consumer:** reads `notifications.outcome` and sets the monolith row's status to `sent` or `failed`. The update is forward-only, so a repeated message does nothing.
- **State lives:** the monolith `notifications` table is still the first record of every notification. The broker holds messages in transit. The monolith worker skips `route = 'service'` rows.
- **If something fails:**
  - Crash after the broker confirms but before `handed_off_at` is set: the row is published again. The service ignores it, because its `id` already exists.
  - Broker down: the relay retries. Rows keep no `handed_off_at`, so nothing is lost.
  - Repeated outcome message: the forward-only update makes it harmless.
  - Extra load: the relay is a small polling query on the monolith. Watch database load, since this is the only sending-related work that stays in the monolith.

### 5. Move `shipping_update` to the service

- **Starts when:** `notify.route.shipping_update` is set to `service`. Within about 10 s, new `shipping_update` rows get `route = 'service'`.
- **Data moves:** new `shipping_update` rows go through the relay (step 4), then to the service (step 3).
- **State lives:** as in steps 3 and 4. Rows already routed to the monolith finish there and are not re-sent.
- **If something fails:** roll back (see Rollback below).
- **Duration:** at least 3 days on the service before step 6 starts.

### 6. Move `order_confirmed` to the service

- **Starts when:** `shipping_update` has run on the service for 3 days with no unexplained failures. Then set `notify.route.order_confirmed` to `service`.
- **Data moves and state:** the same as step 5.
- **If something fails:** roll back.
- **Duration:** at least 3 days on the service. During this time, record enqueue-to-MailRelay latency for this type: the time from the row's `created_at` (set at enqueue in the monolith) to the service's accepted time. Step 7 depends on this p99 value, the 99th percentile. A p99 under 60 s means 99% of notifications were sent faster than that.

### 7. Move `password_reset` to the service

- **Starts when:** `order_confirmed` has run on the service for at least 3 days, and its p99 enqueue-to-MailRelay latency stayed under 60 s during that time. Then set `notify.route.password_reset` to `service`.
- **Data moves and state:** the same as step 5.
- **If something fails:** roll back. This type is the most sensitive to latency, so track p99 hourly.

### 8. Remove the old worker

- **Starts when:** `password_reset` has run on the service for 7 days. Until then, keep the old worker deployed, because rollback depends on it.
- **Steps:**
  1. Confirm that no row routed to the monolith is still waiting to be sent.
  2. Remove the monolith sending loop and its code path.
  3. Keep the `route` column and the relay until the service-routed backlog is empty.
- **If something fails:** if unsent monolith rows exist, do not remove the worker. Investigate first.
- **After removal:** a flag flip can no longer move traffic back to the monolith. Rolling back then means redeploying the old worker code. This is the one step that makes rollback slower.

## Rollback (for steps 5 to 7)

Moving any type back to the monolith is a flag flip:

- Set `notify.route.<type>` to `monolith`.
- The change reaches every instance within about 10 s. New rows of that type then get `route = 'monolith'`, and the monolith worker sends them within about a minute.
- Rows already routed to the service stay there. They are not moved and not re-sent. The relay keeps handing them off, and the service sends each one once.
- If the service is down, rows not yet handed off wait in the monolith's table. Rows already handed to the broker wait on the broker until the service recovers. They are delayed, not lost.
- Do not edit `route` values by hand. Fix the service instead.
- Keep the relay running until the service-routed backlog is empty.

## Checks during every move

- **Relay backlog:** the age of the oldest row with no `handed_off_at`.
- **Failed count and pages:** `failed` rows in the monolith `notifications` table and in the service `deliveries` table, plus on-call pages.
- **Latency:** p99 enqueue-to-MailRelay, per type and per hour.
- **Reconciliation:** a daily job that lists every committed notification that is neither `sent` nor `failed` after a set time. This checks "nothing lost."
- **Duplicates:** support reports of duplicate emails, compared with the baseline of about 30 a week.

## Open questions (answer before step 3)

- **Broker retention:** how long does the broker keep unacknowledged messages? If it can redeliver a message more than 24 hours after its first delivery, the MailRelay 24-hour window no longer protects against duplicates. The rule for old rows in step 3 depends on this answer.
- **`deliveries` retention:** keep rows at least as long as both the broker's retention and MailRelay's 24-hour window, so duplicates are still caught.
- **Personal data on the broker:** email addresses and payloads will now cross the broker. Confirm this is allowed.