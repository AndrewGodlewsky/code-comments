# Refunds from the admin page: implementation plan

Steps are in the order they run. Each step gives what starts it, the data it moves, where state is stored, and what happens on failure. Amounts are integer cents throughout.

**Assumptions**
- The provider offers a refund status lookup by its refund id, and a way to find a refund by our idempotency key or metadata if our system never stored the provider id. Confirm both before building step 13.
- The provider's idempotency window is 24 hours (per the brief). All retry and sweeper deadlines below stay well inside it.
- Our payments table has `id`, `charge_id`, `captured_cents` and `status`.

## Steps

- [ ] **1. Admin opens the payment page**
  - Starts when: an admin with access to the order requests the payment page.
  - Data moves: server loads the payment, its refunds, and the caller's permissions. It computes `refundable_cents = captured_cents - SUM(amount_cents of refunds in pending or succeeded)`.
  - Stored in: read-only from the payments and refunds tables. Nothing is written.
  - On failure: payment not found or not captured gives a 404 or a "not refundable" notice. Users without refund permission see the history but no refund form. A database error shows an error page, and nothing is written.

- [ ] **2. Admin submits the refund form**
  - Starts when: the admin posts amount in cents, reason (one of `duplicate`, `fraudulent`, `customer_request`, `other`), optional note, and a per-form request id generated when the form was rendered.
  - Data moves: the server checks authentication, the refund permission, that `payment.status = captured`, that the amount is a positive integer, that the reason is on the list, and that the note is within a length limit.
  - Stored in: an audit entry is written for every request, including rejected ones. It records the admin, payment, requested amount, reason, request id, result, and time. The request id makes double-clicks and resubmits safe: a repeated request id returns the existing outcome.
  - On failure: a validation or permission failure returns an inline error and creates no refund. The rejection is still audited.

- [ ] **3. Reserve the amount and create the refund row (one database transaction)**
  - Starts when: step 2 passes validation.
  - Data moves: `SELECT ... FROM payments WHERE id = ? FOR UPDATE` takes a row lock, so two admins refunding the same payment at the same moment serialise here. The server recomputes the sum of pending and succeeded refunds. If `sum + amount_cents > captured_cents`, it rejects. Otherwise it inserts a refund row with `status = pending`, a new `idempotency_key` (UUID v4, generated and stored before any provider call), `attempts = 0`, and the reason and note. It also writes an audit entry "refund requested".
  - Stored in: `refunds` (new table: `id`, `payment_id`, `amount_cents`, `reason`, `note`, `status`, `idempotency_key` unique, `provider_refund_id` nullable, `attempts`, `last_attempt_at`, `last_status_check_at`, `failure_message`, `created_by`, `created_at`, `updated_at`). Also `audit_log` (append-only).
  - Why this design: a pending refund counts toward the cap from the moment it is reserved, so the cap holds before any network call. The lock is released before the provider call, so no database lock is held over the network.
  - On failure: cap exceeded rolls back, with no row and a clear message to the admin. A database error rolls back the transaction, so no reservation exists and the admin can retry.

- [ ] **4. Call the provider's create-refund API (server only)**
  - Starts when: step 3 commits.
  - Data moves: the server sends the provider charge id, `amount_cents`, the idempotency key, and metadata with our refund id. Before each attempt, it increments `attempts` and sets `last_attempt_at` in its own transaction. The browser is never involved.
  - Stored in: `refunds.attempts`, `last_attempt_at`, and one audit entry per attempt.
  - Timeout: 10 seconds per call.
  - On failure: see step 5.

- [ ] **5. Interpret the provider response**
  - **5a. 2xx (accepted).** Store `provider_refund_id`. Keep `status = pending`, because "accepted" is not final. Write an audit entry "provider accepted". If the write fails after the provider accepted, the row stays pending with no provider id. Step 9 resolves it by repeating the call with the same key, which returns the original refund.
  - **5b. 4xx (rejected).** Before marking the refund failed, check whether an earlier timed-out attempt may have created it. If one did, look up its status first (step 9) rather than trusting the rejection. Otherwise set `status = failed`, store the provider's message in `failure_message`, write an audit entry, and return the message to the admin. Do not retry. A failed refund no longer counts toward the cap.
  - **5c. Timeout or 5xx.** Retry the same call with the same idempotency key, up to 3 retries (4 attempts in total), with a short backoff such as 1s, 2s and 4s. Each attempt is audited. If all attempts fail, the refund stays `pending` and is flagged "unconfirmed". It is never marked failed, because the provider may have created it. Step 9 resolves it.
  - Stored in: `refunds` (`status`, `provider_refund_id`, `failure_message`, `attempts`, `updated_at`) and `audit_log`.

- [ ] **6. Show the admin the immediate result**
  - Starts when: step 5 reaches a state.
  - Data moves: the admin sees "Refund submitted, awaiting provider confirmation" (pending), the provider's message (failed), or a retry-later notice (unconfirmed).
  - Stored in: nothing new. The page reads the refund row.
  - On failure: if the admin's browser drops, the outcome is still on the payment page, because the state lives in the database and not in the response.

- [ ] **7. Receive a provider webhook**
  - Starts when: the provider posts `refund.succeeded` or `refund.failed`.
  - Data moves: the server verifies the signature against the raw request body. It extracts the provider event id and the provider refund id.
  - Stored in: `webhook_events` (new table, `provider_event_id` unique, `payload`, `received_at`, `processed_at`, `result`). The event is inserted before the server replies 2xx, so the provider retries if the insert fails.
  - On failure: a bad signature returns 401 and writes an audit entry, with nothing stored. A duplicate event id returns 200 and does nothing, because the unique key makes delivery idempotent. A storage failure returns 500 so the provider retries.

- [ ] **8. Apply a webhook event (out-of-order and duplicate safe)**
  - Starts when: step 7 stores a new event. It may also be run later by step 9 for events that were unmatched.
  - Data moves: look up the refund by `provider_refund_id`. If no row matches (the event arrived before step 5a stored the id), mark the event `unmatched` and leave it for a later pass. Otherwise apply the transition with a conditional update: `UPDATE refunds SET status = ? WHERE id = ? AND status = 'pending'`. This makes terminal states final, so a late `refund.failed` after `succeeded`, or a repeat of either, changes nothing and is logged.
  - Stored in: `refunds`, `webhook_events.result`, and `audit_log` (from-state, to-state, source "webhook", event id), written in the same transaction as the status change.
  - On failure: a transaction failure rolls back both the status change and its audit entry. The event stays unprocessed and is retried by step 9.

- [ ] **9. Sweeper: check pending refunds directly with the provider**
  - Starts when: a scheduled job runs every 30 minutes. It selects refunds where `status = pending` and either `last_status_check_at` is null and the refund is older than 1 hour, or `last_status_check_at` is more than 6 hours ago. The 6-hour cadence leaves a wide margin under the 24-hour rule. Webhooks do not count as a check.
  - Data moves: if the refund has a `provider_refund_id`, fetch its status from the provider with a 10-second timeout. If it has no id, re-send the create call with the stored idempotency key. Within the 24-hour window the provider returns the original refund. Apply the result through the step 8 transition function. Also re-process unmatched webhook events.
  - Stored in: `refunds.last_status_check_at` and `audit_log` (source "sweeper").
  - Deadline: at 18 hours of pending age, raise an alert to the on-call team. Continue checking. Never let an idempotency key pass 24 hours without a resolved outcome, and do not start a new provider call for a refund whose key is older than 23 hours. Mark it for manual review instead.
  - On failure: a provider error or timeout leaves the refund pending. The next run retries. Repeated failures escalate through the alert.

- [ ] **10. Refund succeeds: record the transition and queue the customer email (one transaction)**
  - Starts when: a refund moves from `pending` to `succeeded` in step 8 or step 9.
  - Data moves: in the same transaction as the status change, insert an audit entry (from `pending`, to `succeeded`, source, event or request id) and an `email_outbox` row with a unique key on `(refund_id, 'refund_succeeded')`. The unique key is what guarantees one email per refund, even if the transition is applied twice.
  - Stored in: `refunds`, `audit_log`, `email_outbox` (new table: `id`, `refund_id`, `type`, `status`, `attempts`, `sent_at`).
  - On failure: if the transaction fails, nothing is queued and the status stays pending, so step 9 will try again.

- [ ] **11. Refund fails: record the transition (no email)**
  - Starts when: a refund moves to `failed`, from step 5b or from a webhook or sweeper in steps 8 and 9.
  - Data moves: status to `failed`, the provider message, and an audit entry in the same transaction. No email is queued. The refunded total drops, and the admin can start a new refund with a new key.
  - Stored in: `refunds`, `audit_log`.
  - On failure: as in step 10. The conditional update prevents a second terminal transition.

- [ ] **12. Send the customer email (outbox worker)**
  - Starts when: the worker finds `email_outbox` rows where `status = queued`. It runs every minute.
  - Data moves: the worker reads the refund and payment, then sends the email. It passes the outbox row id as the email provider's idempotency key, if the provider supports one.
  - Stored in: `email_outbox.status`, `attempts`, `sent_at`, and an audit entry on success.
  - On failure: a send error increments `attempts` and retries with backoff. After a fixed number of attempts, the row is marked `dead` and an alert is raised for manual follow-up. If the worker crashes after sending but before marking sent, a duplicate is possible unless the email provider honours the idempotency key. Record this as a known limitation if no key is available.

- [ ] **13. Derive the order's refund label**
  - Starts when: any refund changes status to `succeeded` (step 10), or when the payment page is loaded.
  - Data moves: `SUM(amount_cents)` over `succeeded` refunds only, compared with `captured_cents`. If the sum is 0, show no label. If the sum is less than captured, show "Partially refunded". If it equals captured, show "Refunded". Pending and failed refunds are not counted.
  - Stored in: computed on read from `refunds`. If a stored label is ever added for reporting, it must be updated in the same transaction as step 10, to avoid drift.
  - On failure: if the read fails, the page shows an error and no label. It never shows a guessed label.

- [ ] **14. Audit every request and status change**
  - Starts when: each of steps 2, 3, 4 (per attempt), 5, 7, 8, 9, 10, 11 and 12 writes state.
  - Data moves: each `audit_log` entry records actor (admin id or "system"), action, refund id, payment id, from-state, to-state, amount, reason, provider ids, source (admin, provider call, webhook, sweeper, outbox), request or event id, and timestamp.
  - Stored in: `audit_log`, append-only, written in the same transaction as the change it records. The application database role cannot update or delete rows in this table.
  - On failure: if the audit write fails, the change it records rolls back. No state change happens without its audit entry.

- [ ] **15. Final outcome is recorded**
  - Starts when: the refund reaches a terminal state, `succeeded` or `failed`, and any customer email is `sent` or `dead`.
  - Data moves: a final audit entry "refund closed" with the outcome, the total refunded for the payment after this refund, and the order label from step 13.
  - Stored in: `refunds` (terminal status with `updated_at`), `audit_log`, `email_outbox`.
  - On failure: if the closing entry cannot be written, the refund stays in its terminal state. A reconciliation report lists terminal refunds that lack a closing entry, so they can be fixed later.
  - End of process.

## Verification to build alongside the steps
- Two concurrent refund requests on the same payment, sized so that only one fits under the cap. Exactly one row is created.
- Simulated timeouts and 5xx responses. The same idempotency key is reused, and the refund is never marked failed while unconfirmed.
- Webhooks delivered twice and out of order (`failed` then `succeeded`, and `succeeded` then `failed`). The terminal state is unchanged and the email is queued once.
- A pending refund with no webhook. The sweeper resolves it before the 24-hour mark.
- A 4xx response. The refund is failed, the message is shown, and the refundable amount increases.
