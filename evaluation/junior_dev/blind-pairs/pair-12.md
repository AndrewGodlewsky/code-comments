# Pair 12

Which document would a smart engineer who does not know this project understand faster and more correctly?

---

# Document A

# Refunds plan

Admins issue full or partial refunds from our own admin page. Our server calls the card provider's refund API and records every refund in our database. The browser never contacts the provider.

## How it works in brief

1. The server reserves the amount by inserting a `pending` refund row inside a database transaction that locks the payment row.
2. The server asks the provider to create the refund. The provider's reply only means "accepted".
3. The final result (`succeeded` or `failed`) arrives later, usually by webhook (a message the provider sends to our server). It can take days. A periodic reconciliation job asks the provider directly, in case a webhook is lost.
4. One shared routine applies the final result, updates the order and queues the customer email. The webhook and the reconciliation job both use it.

## Terms and records

- **Captured amount**: the money already collected on a payment, in cents. Only captured payments can be refunded.
- **Refund status**: `pending` (sent to the provider, no final answer yet), `succeeded` or `failed`. Only `pending` can change, and only to `succeeded` or `failed`.
- **Open total** of a payment: the sum of its `pending` and `succeeded` refunds. `failed` refunds are excluded. The open total must never exceed the captured amount.
- **Idempotency key**: a value we send with the provider's create-refund call. If the provider receives the same key again within 24 hours, it returns the original refund instead of creating a new one. This makes retries safe.
- **`refunds` table (new)**:
  - `id`
  - `payment_id`
  - `amount_cents`
  - `reason`: one of `duplicate`, `fraudulent`, `customer_request`, `other`
  - `note` (optional free text)
  - `status`
  - `idempotency_key`: generated once, unique, reused on every retry
  - `provider_refund_id`: empty until the provider answers
  - `failure_message`
  - `created_by`
  - `created_at`
  - `last_checked_at`
  - `emailed_at`
- **`refund_audit` table (new)**: `refund_id` (empty if no refund row was created), `payment_id`, `actor` (an admin id, `provider-webhook` or `reconciler`), `action`, `old_status`, `new_status`, `detail`, `at`.
- **`webhook_events` table (new)**: one row per provider event id, with a unique constraint. It is used to ignore duplicate deliveries.
- **`payments` table (existing)**: provider charge id, captured amount, status. This plan also adds a refund display status for the order ("Partially refunded" or "Refunded").

## Steps, in order

- [ ] **1. Admin opens the payment page**
  - Starts when: an admin opens a payment in the admin page.
  - Data moves: the server returns the captured amount, the open total, the amount remaining (captured minus open total) and the existing refunds with their statuses. The refund form (amount, reason, optional note) is shown only if the payment is captured and the admin has refund permission. Hiding the form is only a convenience. Step 3 checks again on the server.
  - State stored: nothing is written.
  - On failure: if the payment is not captured or the admin lacks permission, the form is not shown.

- [ ] **2. Admin submits the form**
  - Starts when: the admin clicks Refund.
  - Data moves: the browser sends `POST /refunds` to our server with `payment_id`, `amount_cents`, `reason` and `note`.
  - State stored: nothing yet.
  - On failure: if the request fails or times out, the page shows an error. The admin can reload the page to see whether a refund row was created (step 4).

- [ ] **3. Server checks permission and input**
  - Starts when: the request arrives.
  - Data moves: the server checks that the admin is logged in and has refund permission, that `reason` is in the fixed list, that `amount_cents` is a whole number greater than 0, and that the payment is captured.
  - State stored: an audit entry `refund_requested` is written for every request, including rejected ones. It records who, the amount, when, and the outcome.
  - On failure: the server returns 403 for missing permission, or 422 for bad input or an uncaptured payment. No refund row is created, and the page shows the message.

- [ ] **4. Reserve the amount and create the refund row (one database transaction)**
  - Starts when: step 3 passes.
  - Data moves: inside one transaction the server locks the payment row (`SELECT ... FOR UPDATE`) and sums its `pending` and `succeeded` refunds. If open total + requested amount is no more than the captured amount, it inserts a `pending` refund with a newly generated `idempotency_key`, then commits.
  - Concurrency: the lock makes two admins refunding the same payment at the same moment run one after the other. The second admin sees the first refund's reserved amount and is rejected if too little remains. The provider call happens after the commit, so the lock is never held during a network call.
  - State stored: a new `refunds` row with status `pending`, plus audit entry `refund_created`, written in the same transaction.
  - On failure: if the amount exceeds what is left, the transaction rolls back, nothing is created, and the server returns 422 with the remaining amount. If the database fails, the transaction rolls back and the server returns 500.

- [ ] **5. Call the provider's create-refund API**
  - Starts when: step 4 has committed. This runs inside the same web request, so the admin waits for it.
  - Data moves: the server sends the provider the charge id, the amount, the refund's `idempotency_key`, and our refund id as metadata. The provider returns an "accepted" response containing its refund id. "Accepted" is not the final result. Each attempt has a 10-second timeout.
  - Retries: on a timeout or a 5xx response, retry up to 3 more times (4 attempts in all) with short pauses (for example 1s, 2s, 4s) and the same idempotency key. If an earlier attempt actually created the refund, the provider returns that original refund, so no duplicate is made.
  - Worst-case wait: about 47 seconds (4 attempts of 10s plus 7s of pauses), so the form shows a spinner.
  - State stored: on "accepted", `provider_refund_id` is saved on the row and the status stays `pending`. Audit entry: `sent_to_provider`.
  - On failure: see step 6.

- [ ] **6. Handle the provider's answer**
  - Starts when: step 5 gets an answer, or runs out of retries.
  - Accepted (2xx): the server returns 201 with the refund as `pending`. The page shows "Refund pending".
  - Rejected (4xx): the provider has refused the refund. The server does not retry. It sets the status to `failed`, saves the provider's message in `failure_message`, and writes audit entry `status_changed pending→failed`. It returns 422 and the page shows the provider's message. Because `failed` refunds are not part of the open total, the reserved amount becomes available again.
  - Timeout or 5xx after all retries: the outcome is unknown, because the provider may have created the refund anyway. The server does not mark the refund `failed`. It leaves the status `pending` with no `provider_refund_id`, writes audit entry `provider_unreachable`, and returns 202 with "Refund submitted, status unconfirmed". The reconciliation job (step 9) settles the outcome.

- [ ] **7. Provider webhook arrives (the usual way a refund reaches its final state)**
  - Starts when: the provider sends `refund.succeeded` or `refund.failed` to our webhook endpoint. This can happen seconds or days after step 5. Webhooks can be delivered more than once and out of order.
  - Data moves: the provider posts the event (event id, provider refund id, result, failure message) with a signature header. The server verifies the signature against the raw request body using the shared secret, and rejects the event if it does not match. It then finds our refund by `provider_refund_id`. If the event arrives before step 5 saved that id, the server finds the refund using the refund id we sent as metadata. It then passes the result to step 8.
  - Duplicates: step 8 inserts the event id into `webhook_events` in the same transaction that applies the status. A repeated delivery hits the unique constraint, is acknowledged with 200 and is ignored. Using the same transaction matters: if the status update fails and rolls back, the event id is rolled back too, so the provider's redelivery is processed instead of being ignored.
  - State stored: nothing here. Step 8 does the writing.
  - On failure: an invalid signature gets 400, nothing is changed, and audit entry `bad_signature` is written. If the refund cannot be found, or processing fails, the server returns 500 so the provider redelivers later.

- [ ] **8. Apply the final status (one shared routine, used by both the webhook and the reconciler)**
  - Starts when: step 7 or step 9 has a final result for a refund.
  - Data moves: in one database transaction the server does the following.
    1. For a webhook, insert the event id into `webhook_events`.
    2. Run `UPDATE refunds SET status = :result WHERE id = :id AND status = 'pending'`. The `status = 'pending'` condition makes this safe against duplicate events, out-of-order events, and the webhook and reconciler racing each other.
    3. If 0 rows changed, the refund already has a final status, so nothing more happens. If that existing status disagrees with the new result (for example `succeeded` followed by `failed`), nothing is changed, audit entry `conflict` is written, and an alert is raised for a person to look at.
  - State stored: if 1 row changed, the new status is saved (plus `failure_message` for `failed`), and audit entry `status_changed pending→succeeded` or `pending→failed` is written with actor `provider-webhook` or `reconciler`. For `succeeded`, step 10 (order status) runs in the same transaction, and a customer-email job is queued (step 11), also in the same transaction.
  - On failure: the transaction rolls back and the status stays `pending`. The provider redelivers the webhook, or the reconciler tries again later.

- [ ] **9. Reconciliation job (checks status with the provider directly)**
  - Starts when: a scheduler runs it every 15 minutes. Webhooks alone are not enough, because they can be lost.
  - Data moves: the job selects `pending` refunds that were last checked more than 1 hour ago, or never. For each one it asks the provider for the refund's status.
    - If the refund has a `provider_refund_id`, it looks the refund up by that id.
    - If not (step 6, retries exhausted), it repeats the create-refund call with the same idempotency key. This is safe within 24 hours, because the provider returns the original refund or creates it exactly once.
    - If the provider's answer is final, the job passes it to step 8.
  - State stored: `last_checked_at` is updated on every check, and `provider_refund_id` is saved if it was missing. When the status changes, step 8 writes the audit entry, with actor `reconciler`.
  - Guarantee: with a 15-minute schedule and a 1-hour recheck interval, no refund stays `pending` for 24 hours without being checked.
  - On failure: if the provider cannot be reached, nothing changes and the refund is picked up on the next run. A refund still `pending` after 24 hours with no `provider_refund_id` can no longer be safely re-sent with the same key, so it raises an alert for a person to resolve.

- [ ] **10. Update the order's refund status**
  - Starts when: step 8 changes a refund to `succeeded`. This runs in the same transaction.
  - Data moves: the server recomputes the total of `succeeded` refunds on the payment from the database. It does not add to a stored number, so replays cannot double count. If the total is greater than 0 and less than the captured amount, the order shows "Partially refunded". If it equals the captured amount, the order shows "Refunded". `pending` and `failed` refunds are ignored.
  - State stored: the order's refund status is written. Audit entry: `order_status_changed`.
  - On failure: the whole step 8 transaction rolls back and is retried through the webhook or the reconciler.

- [ ] **11. Email the customer (only after success, only once)**
  - Starts when: the email job picks up the job queued in step 8.
  - Data moves: the job sends the customer a refund-confirmation email with the amount and the order. A job is queued only when a refund first becomes `succeeded` (step 8's conditional update), and the queue allows one job per refund. So duplicate webhook deliveries cannot cause a second email. No email is sent for `failed` refunds.
  - State stored: `emailed_at` is set on the refund after the email is sent. Audit entry: `customer_emailed`.
  - On failure: if sending fails, the job is retried until it works, and `emailed_at` stays empty. A small risk remains: a crash right after sending but before `emailed_at` is saved could cause a second email. If the email service supports an idempotency key, use the refund id as that key to close this gap.

- [ ] **12. Final outcome is recorded**
  - The refund has a final status (`succeeded` or `failed`) with its audit history, and the order shows the matching refund status. The admin page shows the final status and, for `failed`, the provider's message.
  - Audit entries written along the way: `refund_requested`, `refund_created`, `sent_to_provider`, `provider_unreachable`, `status_changed`, `order_status_changed`, `customer_emailed`, plus `conflict` and `bad_signature`. Each records who, what and when.

## Assumptions to confirm

- The provider can attach our refund id as metadata and can look up a refund by its id.
- A 15-minute reconciler schedule and a 1-hour recheck interval are acceptable.
- The admin may wait up to about 47 seconds on the provider call. If not, step 5 moves to a background worker, and a 4xx message from step 6 would reach the admin only when they reload the page.

---

# Document B

# Refunds plan

Today, support staff refund customers in the card provider's dashboard, so our database never learns that a refund happened. This plan lets admins issue full and partial refunds from our own admin page. Our server records each refund as `pending` and asks the provider to refund it. The provider's final answer arrives later by webhook, and a scheduled job checks any refund the webhook has not settled. Every change is recorded in our own database and in an audit log.

We already store payments with the provider's charge id, the captured amount (in cents) and a status. There is no refund table yet; this plan adds one.

## Terms

- **Captured**: the payment's money has been taken. Only captured payments can be refunded.
- **Provider**: the card company whose API moves the money.
- **Idempotency key**: a value we send with a create-refund call. If the provider sees the same key again within 24 hours, it returns the original refund instead of making a new one. Our key is the refund's own `id`.
- **Webhook**: a signed HTTP call the provider makes to our server to report a result. It can arrive more than once and out of order.
- **Accepted**: the provider's immediate reply. It does not mean the money has moved. The final result is a `refund.succeeded` or `refund.failed` webhook, sometimes days later.
- **Pending / succeeded / failed**: the three values of a refund's `status`. Only `pending` can change. `succeeded` and `failed` are final.
- **What is left**: the payment's captured amount minus the sum of its `pending` and `succeeded` refunds. `failed` refunds do not count.

## Rules that hold in every step

- Amounts are whole cents. A payment can have several partial refunds. The total of pending and succeeded refunds must never exceed the captured amount, even when two admins refund the same payment at once.
- Only an admin with refund permission can refund, and only on a captured payment.
- Every refund has a reason from a fixed list (duplicate, fraudulent, customer request, other) and an optional free-text note.
- Only our server talks to the provider. The browser never does.
- No refund may stay `pending` for more than 24 hours without our system asking the provider for its status directly. Webhooks alone are not enough.
- The customer is emailed only after the refund has succeeded, and only once per refund.
- The order shows "Partially refunded" or "Refunded" based on succeeded refunds only.
- Every refund request and every status change gets an audit entry (who, what, when). Webhooks and the job write theirs as "system".

## Steps, in the order they happen

- [ ] **1. Admin opens the payment page.** The page shows a refund form (amount in cents, reason, optional note) and a list of this payment's refunds with their status. The form is hidden for payments that are not captured and for admins without refund permission. It only reads data, so nothing can fail here.
- [ ] **2. Admin submits the form: `POST /refunds`.** The browser sends `payment_id`, `amount_cents`, `reason` and `note`. The server checks the permission, that the payment is captured, that the amount is a whole number above 0, and that the reason is in the list. No permission gives 403 and the form says "You do not have permission to refund". Any other bad input gives 400 and the form says what is wrong. In both cases nothing is stored and nothing is sent to the provider.
- [ ] **3. Check what is left, and create the refund record.** Both happen in one database transaction. The transaction first locks the payment row, so two admins refunding the same payment are handled one after the other. It computes what is left fresh from the `refunds` table. If the amount is more than what is left, it rolls back, the server returns 409 and the form shows how much is left. Otherwise it inserts the refund with `status` `pending` and writes the audit entry, and the commit releases the lock. The record is created before any provider call, so the money is reserved. If the transaction itself fails, nothing is stored, and the admin sees a generic error and can retry.
  - Table `refunds`: `id` (a UUID, also the idempotency key), `payment_id`, `amount_cents`, `reason`, `note`, `status`, `provider_refund_id` (empty until the provider answers), `failure_message`, `requested_by`, `email_sent_at`, `created_at`, `updated_at`.
  - Table `audit_log`: who, what, when, refund id, old status, new status.
- [ ] **4. Call the provider's create-refund API, after the commit.** The call sends the payment's charge id and the amount, with the refund `id` as the idempotency key. Timeout is 10 seconds. On a timeout or a 5xx, retry up to 3 times with the same key, so a retry can never refund twice.
  - Accepted: save `provider_refund_id` and keep `pending`.
  - 4xx: the provider rejected the refund (for example the charge is already fully refunded). Do not retry. Set `failed`, save the provider's message in `failure_message`, write the audit entry in the same transaction, and show the admin that message. A failed refund no longer counts toward what is left, so the amount is available again.
  - Every retry fails: the refund stays `pending` with no `provider_refund_id`, and the admin sees "Refund requested, awaiting provider". We cannot tell whether the provider received it. Step 8 sorts it out.
  - `POST /refunds` returns after this step, not after the webhook, which can take days. Its response is the refund's current status (`pending`, or `failed` with the message). The admin sees the final result by reloading the payment page.
- [ ] **5. Provider sends a webhook (`refund.succeeded` or `refund.failed`).** The server first verifies the signature over the raw request body with the provider's shared secret, before reading anything else. An invalid signature gets 400, is ignored and is logged. A valid event is matched to our refund by `provider_refund_id`. If no refund matches yet (the event arrived before step 4 saved the id), return a non-2xx code so the provider redelivers later. Otherwise apply step 6 and reply 200. If our processing errors, return 500 so the provider redelivers.
- [ ] **6. Update the refund status.** This runs for each valid webhook and for each result found by step 8. The update only applies while the refund is still `pending` (`UPDATE ... WHERE status = 'pending'`), so running it twice is safe. A duplicate event, or a later one that contradicts the final state (for example `failed` after `succeeded`), changes nothing. The contradiction is written to the audit log for a human to see. A change to `succeeded` or `failed` writes its audit entry in the same transaction. If the transaction fails, it rolls back and the provider redelivers.
- [ ] **7. Update the order status and send the email.**
  - Order status runs in the same transaction as step 6. Sum the payment's `succeeded` refunds: 0 means no change, less than the captured amount means "Partially refunded", equal to it means "Refunded". It is recalculated each time, so a failed or pending refund never changes it.
  - The email runs after that commit, only when this update moved the refund to `succeeded`. The same update sets `email_sent_at`, so only the run that made the change sends, and a duplicate webhook never sends a second email. If sending fails, log it and clear `email_sent_at` so step 8 retries it.
- [ ] **8. Reconciliation job (checks the provider directly).** It runs every 15 minutes and finds refunds that are `pending` and older than 1 hour, well inside the 24-hour limit.
  - With a `provider_refund_id`: ask the provider for the refund's status and apply the result through step 6.
  - Without one, and under 24 hours old: repeat the create call with the same key. The provider returns the original refund, so this is safe.
  - Without one, and past 24 hours: the key has expired, so repeating is no longer safe. Mark it `failed` with a message, and a human checks the provider dashboard.
  - It also resends the email for `succeeded` refunds with no `email_sent_at`.
  - Errors are logged and the job tries again at its next run.

## What happens when things fail

| Where | What goes wrong | Result |
|---|---|---|
| 2 | No permission / bad input | 403 / 400, nothing stored |
| 3 | Amount above what is left | 409, rolled back, nothing stored |
| 3 | Transaction fails | Nothing stored, admin can retry |
| 4 | Provider 4xx | `failed` with provider message, no retry |
| 4 | Timeout or 5xx after 3 retries | Stays `pending`, step 8 resolves it |
| 5 | Invalid signature | 400, ignored, logged |
| 5 | No matching refund yet | Non-2xx, provider redelivers |
| 5, 6 | Our processing or update fails | 500 or rollback, provider redelivers |
| 6 | Duplicate or contradicting event | No change, contradiction audited |
| 7 | Email fails | `email_sent_at` cleared, step 8 retries |
| 8 | Job run fails | Logged, next run retries |

## Open questions

- Does the provider let us attach our refund `id` to the refund, or look up a refund by idempotency key? If yes, webhooks that arrive before step 4 saves `provider_refund_id`, and refunds past the 24-hour key window, can be matched without a human.
- The job's timings (every 15 minutes, refunds older than 1 hour) are my choices, not from the brief.
- The signature algorithm follows the provider's documentation and is not decided here.
