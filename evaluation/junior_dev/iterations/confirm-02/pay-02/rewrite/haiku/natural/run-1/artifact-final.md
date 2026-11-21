# Refunds from the admin page: implementation plan

Today support staff refund customers in the card provider's dashboard, so our database never learns that a refund happened. This plan lets admins issue full or partial refunds from our own admin page. Our server calls the provider's refund API and keeps its own record of every refund. A refund is saved as `pending` before the provider is called, so it counts toward the limit at once. It becomes `succeeded` or `failed` only when the provider confirms the final result, through a webhook or through a scheduled check.

## Terms

- **Captured**: the customer's card charge has been taken. Only captured payments can be refunded.
- **Provider**: the card payment company. Only our server calls its API.
- **Idempotency key**: a unique id we send with each create-refund call. If the provider receives the same key again within 24 hours, it returns the original refund instead of making a new one.
- **UUID v4**: a randomly generated id that is effectively unique.
- **Refund status**: `pending` (sent, not final), `succeeded` (final, done) or `failed` (final, not done). `succeeded` and `failed` are terminal: once set, they never change.
- **Webhook**: a message the provider posts to our server when a refund's result is known. It is signed, so we can check that the provider sent it.
- **Row lock**: a database lock (`SELECT ... FOR UPDATE`) that makes other transactions on the same row wait until ours ends.
- **Conditional update**: an update that changes a row only if the row still has the status we expect.
- **Audit log**: a table of who did what and when. Rows are only added, never changed or deleted.
- **Outbox**: a table of emails waiting to be sent. A worker sends them.
- **Sweeper**: a scheduled job that asks the provider directly about refunds that are still pending.
- **Unconfirmed**: a pending refund where every call attempt timed out or got a 5xx, so we do not know whether the provider created it.
- **Unmatched event**: a webhook for a refund id that we have not stored yet.

## Assumptions

- The provider offers a status lookup by its refund id. It also offers a way to find a refund by our idempotency key or metadata, for when we never stored its provider id. Confirm both before building the sweeper (step 9), which needs them.
- The provider's idempotency window is 24 hours (from the brief). All retry and sweeper deadlines below stay well inside it.
- Our payments table has `id`, `charge_id`, `captured_cents` and `status`.

## Rules that apply at every step

- Amounts are integer cents everywhere.
- The browser never talks to the provider. Only the server does.
- Every change to a refund writes an audit entry in the same transaction as the change. Each entry records the actor (admin id or "system"), action, refund id, payment id, from-state, to-state, amount, reason, provider ids, source (admin, provider call, webhook, sweeper or outbox), request or event id, and timestamp.
- The audit log is append-only. The application's database role cannot update or delete its rows.
- If the audit write fails, the change it records is rolled back. No state changes without its entry.

## Steps

Steps run in the order listed. Each step says what starts it, what data moves, where state is stored, and what happens on failure.

- [ ] **1. Admin opens the payment page**
  - Starts when: an admin with access to the order opens the payment page.
  - Data moves: the server loads the payment, its refunds and the admin's permissions. It computes `refundable_cents = captured_cents - SUM(amount_cents)` over refunds that are `pending` or `succeeded`.
  - Stored in: read only. Nothing is written.
  - On failure: a payment that is not found, or not captured, gives a 404 or a "not refundable" notice. Admins without refund permission see the history but no refund form. A database error shows an error page and writes nothing.

- [ ] **2. Admin submits the refund form**
  - Starts when: the admin posts an amount in cents, a reason (`duplicate`, `fraudulent`, `customer_request` or `other`), an optional note, and a request id that was generated when the form was shown.
  - Data moves: the server checks that the admin is logged in, has refund permission, that the payment's `status` is `captured`, that the amount is a positive integer, that the reason is on the list, and that the note is within its length limit.
  - Stored in: an audit entry for every request, including rejected ones. The request id makes double-clicks and resubmits safe: a repeated request id returns the existing outcome.
  - On failure: a validation or permission failure shows an inline error and creates no refund. The rejection is still audited.

- [ ] **3. Reserve the amount and create the refund row (one database transaction)**
  - Starts when: step 2 passes validation.
  - Data moves: the server takes a row lock on the payment (`SELECT ... FROM payments WHERE id = ? FOR UPDATE`). Admins refunding the same payment at the same moment wait here, one after another. The server then recomputes the sum of `pending` and `succeeded` refunds. If `sum + amount_cents > captured_cents`, it rejects. Otherwise it inserts a refund row with `status = pending`, a new idempotency key (a UUID v4, generated and saved before any provider call), `attempts = 0`, and the reason and note. It also writes the audit entry "refund requested".
  - Stored in: `refunds` (new table): `id`, `payment_id`, `amount_cents`, `reason`, `note`, `status`, `idempotency_key` (unique), `provider_refund_id` (empty until step 5a), `attempts`, `last_attempt_at`, `last_status_check_at`, `failure_message`, `created_by`, `created_at`, `updated_at`. Also `audit_log`.
  - Why: a pending refund counts toward the limit from the moment it is reserved, so the limit holds before any network call. The lock ends when this transaction commits, so no database lock is held while we wait on the provider.
  - On failure: if the limit would be exceeded, the transaction rolls back. No row is created and the admin sees a clear message. A database error also rolls back, so no reservation exists and the admin can retry.

- [ ] **4. Call the provider's create-refund API (server only)**
  - Starts when: step 3 commits.
  - Data moves: the server sends the provider charge id, `amount_cents`, the idempotency key, and metadata that holds our refund id. Before each attempt, in its own transaction, it increments `attempts` and sets `last_attempt_at`.
  - Stored in: `refunds.attempts` and `last_attempt_at`, plus one audit entry per attempt.
  - Timeout: 10 seconds per call.
  - On failure: see step 5.

- [ ] **5. Read the provider's response**
  - **5a. 2xx (accepted).** Store `provider_refund_id`. Keep `status = pending`, because "accepted" is not the final result. Write the audit entry "provider accepted". If that write fails after the provider accepted, the row stays `pending` with no provider id. Step 9 resolves it by repeating the call with the same key, which returns the original refund.
  - **5b. 4xx (rejected).** The provider has rejected the refund. Do not retry. First check whether an earlier timed-out attempt may already have created it. If one may have, resolve it with the status check in step 9 instead of trusting the rejection. Otherwise set `status = failed`, store the provider's message in `failure_message`, write the audit entry, and show the message to the admin. Failed refunds no longer count toward the limit.
  - **5c. Timeout or 5xx.** Retry the same call with the same idempotency key, up to 3 retries (4 attempts in total), with a short backoff such as 1s, 2s and 4s. Each attempt is audited. If all attempts fail, the refund stays `pending` and is flagged "unconfirmed". It is never marked `failed`, because the provider may have created it. Step 9 resolves it.
  - Stored in: `refunds` (`status`, `provider_refund_id`, `failure_message`, `attempts`, `updated_at`) and `audit_log`.

- [ ] **6. Show the admin the immediate result**
  - Starts when: step 5 reaches a state.
  - Data moves: the admin sees "Refund submitted, awaiting provider confirmation" (pending), the provider's message (failed), or a retry-later notice (unconfirmed).
  - Stored in: nothing new. The page reads the refund row.
  - On failure: if the admin's browser drops, the outcome is still on the payment page, because it is stored in the database and not only in the response.

- [ ] **7. Receive a provider webhook**
  - Starts when: the provider posts `refund.succeeded` or `refund.failed`.
  - Data moves: the server checks the signature against the raw request body. It then reads the provider's event id and the provider refund id.
  - Stored in: `webhook_events` (new table): `provider_event_id` (unique), `payload`, `received_at`, `processed_at`, `result`. The event is saved before the server replies 2xx, so the provider retries if saving fails.
  - On failure: a bad signature returns 401 and writes an audit entry, and nothing is stored. A duplicate event id returns 200 and does nothing, because the unique key makes delivery safe to repeat. A storage failure returns 500, so the provider retries.

- [ ] **8. Apply a webhook event (safe for duplicates and out-of-order delivery)**
  - Starts when: step 7 stores a new event. Step 9 also runs this for events that were unmatched.
  - Data moves: find the refund by `provider_refund_id`. If none matches, the event arrived before step 5a saved the id. Mark the event `unmatched` and leave it for a later pass. If one matches, apply the transition with a conditional update: `UPDATE refunds SET status = ? WHERE id = ? AND status = 'pending'`. This update is "the transition" that steps 9, 10 and 11 use. Terminal states are final, so a late `refund.failed` after `succeeded`, or a repeat of either event, changes nothing. It is logged instead.
  - Stored in: `refunds`, `webhook_events.result`, and `audit_log` (from-state, to-state, source "webhook", event id). The status change and its audit entry are written in one transaction.
  - On failure: if the transaction fails, both the status change and its audit entry roll back. The event stays unprocessed, and step 9 retries it.

- [ ] **9. Sweeper: check pending refunds directly with the provider**
  - Starts when: a scheduled job runs every 30 minutes. It selects refunds where `status = pending` and either (a) `last_status_check_at` is empty and the refund was created more than 1 hour ago, or (b) `last_status_check_at` is more than 6 hours ago. The 6-hour cadence leaves a wide margin under the 24-hour rule. Webhooks do not count as a check.
  - Data moves: if the refund has a `provider_refund_id`, the job fetches its status from the provider, with a 10-second timeout. If it has no id, the job sends the create call again with the stored idempotency key. Within the 24-hour window the provider returns the original refund. The job applies the result with the transition from step 8. It also reprocesses unmatched webhook events.
  - Stored in: `refunds.last_status_check_at`, and `audit_log` (source "sweeper").
  - Deadlines: at 18 hours of pending age, the job raises an alert to the on-call team and keeps checking. An idempotency key must never pass 24 hours without a resolved outcome. The job does not start a new provider call for a refund whose key is older than 23 hours. It marks that refund for manual review instead.
  - On failure: a provider error or timeout leaves the refund pending. The next run retries. Repeated failures escalate through the alert.

- [ ] **10. Refund succeeds: record it and queue the customer email (one transaction)**
  - Starts when: a refund moves from `pending` to `succeeded` in step 8 or step 9.
  - Data moves: in the same transaction as the status change, insert an audit entry (from `pending`, to `succeeded`, source, event or request id) and an `email_outbox` row. The outbox row has a unique key on `(refund_id, 'refund_succeeded')`. That key guarantees one email per refund, even if the transition is applied twice.
  - Stored in: `refunds`, `audit_log`, and `email_outbox` (new table): `id`, `refund_id`, `type`, `status`, `attempts`, `sent_at`.
  - On failure: if the transaction fails, nothing is queued and the status stays `pending`, so step 9 tries again.

- [ ] **11. Refund fails: record it (no email)**
  - Starts when: a refund moves to `failed`, either from step 5b, or from a webhook or sweeper through steps 8 and 9.
  - Data moves: set `status = failed`, save the provider's message, and write the audit entry, all in one transaction. No email is queued. The refunded total drops, so the admin can start a new refund with a new key.
  - Stored in: `refunds` and `audit_log`.
  - On failure: if the transaction fails, nothing changes. The conditional update in step 8 stops a second terminal change.

- [ ] **12. Send the customer email (outbox worker)**
  - Starts when: a worker, run every minute, finds `email_outbox` rows with `status = queued`.
  - Data moves: the worker reads the refund and payment, then sends the email. It passes the outbox row id as the email provider's idempotency key, if the provider supports one.
  - Stored in: `email_outbox.status`, `attempts` and `sent_at`. An audit entry is written on success.
  - On failure: a send error increments `attempts` and retries with backoff. After a fixed number of attempts, the row is marked `dead` and an alert is raised for manual follow-up. If the worker crashes after sending but before marking the row sent, a duplicate is possible, unless the email provider honours the idempotency key. If no such key exists, record this as a known limitation.

- [ ] **13. Derive the order's refund label**
  - Starts when: any refund changes to `succeeded` (step 10), or the payment page loads.
  - Data moves: sum `amount_cents` over `succeeded` refunds only, and compare the sum with `captured_cents`. If the sum is 0, show no label. If it is less than captured, show "Partially refunded". If it equals captured, show "Refunded". Pending and failed refunds are not counted.
  - Stored in: computed on read from `refunds`. If a stored label is ever added for reporting, it must be updated in the same transaction as step 10, so the two cannot drift apart.
  - On failure: if the read fails, the page shows an error and no label. It never shows a guessed label.

- [ ] **14. Record the final outcome**
  - Starts when: the refund reaches a terminal state (`succeeded` or `failed`), and any customer email is `sent` or `dead`.
  - Data moves: write a final audit entry "refund closed" with the outcome, the total refunded for the payment after this refund, and the order label from step 13.
  - Stored in: `refunds` (terminal status, with `updated_at`), `audit_log`, and `email_outbox`.
  - On failure: if the closing entry cannot be written, the refund stays in its terminal state. A reconciliation report lists terminal refunds that lack a closing entry, so they can be fixed later.
  - End of process.

## What happens when things fail

Each step above lists its own failure handling. Two rules hold across all steps:

- A refund that the provider may have created is never marked `failed` while it is unconfirmed. Step 9 settles it.
- A pending refund counts toward the limit until it is `failed`. A failed refund does not count.

## How to build and check it

Build these checks alongside the steps:

- Two concurrent refund requests on the same payment, sized so that only one fits under the cap. Exactly one row is created.
- Simulated timeouts and 5xx responses. The same idempotency key is reused, and the refund is never marked failed while unconfirmed.
- Webhooks delivered twice and out of order (`failed` then `succeeded`, and `succeeded` then `failed`). The terminal state is unchanged and the email is queued once.
- A pending refund with no webhook. The sweeper resolves it before the 24-hour mark.
- A 4xx response. The refund is failed, the message is shown, and the refundable amount increases.

## Open questions

- The provider's status lookup and find-by-key features are assumed, not confirmed (see Assumptions).
- The number of email attempts before a row is marked `dead` is not set, and neither is the backoff.
- If the write that records a 4xx failure fails, no step retries it. The plan does not yet say how such a refund is found.
- The on-call alert channel and the manual review process are not defined.