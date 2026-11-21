# Refunds plan

This plan covers how an admin issues a refund from our internal admin page. Our server calls the card provider's refund API and records every refund in our own database. The browser never talks to the provider.

The provider answers a refund request in two stages. The first answer only means "accepted". The final result (succeeded or failed) comes later, sometimes days later, as a webhook: a signed message the provider sends to our server. Because webhooks can be lost or delayed, we also check pending refunds ourselves on a schedule.

The steps below are in the order they happen, from the admin opening a payment to the final refund outcome being recorded.

**Terms used below**

- **Captured**: the payment was charged successfully. Only captured payments can be refunded.
- **Refund states**: `pending` (sent to the provider, result not yet known), `succeeded`, or `failed`. `succeeded` and `failed` are final. Nothing changes them after that.
- **Idempotency key**: a unique value sent with a provider call. If we send the same key again within 24 hours, the provider returns the original refund instead of creating a second one. We use the refund's own id as the key.
- **Webhook**: a message the provider sends to our server when a refund's result is known. Each webhook is signed with a secret that only we and the provider know. We check the signature before trusting the message. Webhooks can arrive late, more than once, or out of order. When the provider sends the same webhook again, we say it **redelivers** it.
- **Transaction**: a group of database changes that either all save or all get undone.
- **Row lock**: while one transaction holds a lock on a database row, other transactions must wait before they can change that row.
- **Conditional update**: a change to a row that applies only if a stated condition is still true when the database applies it. The check and the change happen as one step.
- **Audit entry**: a record of who did what, and when. The audit table is append-only, so rows are never edited or deleted.
- **Actor**: who caused a change. This is an admin's user id, `system` (the scheduled reconciliation job), or `provider` (a webhook).
- **Reconciliation**: the scheduled job that asks the provider for the current status of pending refunds.

**Where state lives**

- **Payments** (existing table): charge id, captured amount, payment status.
- **Order** (existing record): order status, either "Partially refunded" or "Refunded".
- **Refunds** (new table): id (also the idempotency key), payment id, amount in cents, reason, note, status, provider refund id, failure message, created by, created at, last checked at, customer emailed at.
- **Audit** (new table, append-only): one row per recorded action.

**Steps, in order**

- [ ] **1. Admin page: refund form on the payment page**
  - Starts when: an admin with refund permission opens a captured payment.
  - Data: the page shows the captured amount and the amount already refunded (pending and succeeded refunds added together). The form asks for an amount in cents, a reason (one of: duplicate, fraudulent, customer request, other), and an optional free-text note. The form also generates a request id, which is sent with the submission.
  - Stored: nothing new.
  - On failure: if the payment is not captured, the form is not shown. If the input is invalid, the error appears on the form and nothing is sent to the server.

- [ ] **2. API endpoint: POST /refunds**
  - Starts when: the admin submits the form. The browser sends the payment id, amount, reason, note and request id.
  - Checks, in order:
    1. The user is logged in and has refund permission. If not, the server returns 403.
    2. The payment exists and is captured. If not, the server returns an error.
  - Stored: one audit entry "refund requested" with the admin's id, the payment id, the amount, the reason and the time. This entry is written in its own transaction, so it is kept even if a later check rejects the request. No refund exists yet, so the refund id is empty.
  - On failure: the error goes back to the form. Nothing else changes. If the audit entry cannot be written, the request is refused and does not go on to step 3.

- [ ] **3. Check the amount against what is left on the payment**
  - Starts when: the request passes step 2.
  - Data: the server starts a transaction and takes a row lock on the payment row. While this transaction holds the lock, any other refund request for the same payment waits. This means two admins refunding the same payment at the same moment cannot both pass this check. The server then computes:
    - remaining = captured amount minus the sum of pending and succeeded refunds.
    - Failed refunds are not counted.
    - The amount must be a whole number of cents, greater than zero, and no more than remaining.
  - Stored: nothing yet.
  - On failure: if the amount is invalid, the transaction ends with nothing saved, and the admin sees the reason. The audit entry from step 2 is kept.

- [ ] **4. Create the refund record**
  - Starts when: step 3 passes. This happens inside the same transaction, so the lock is still held.
  - Data: a new refund row with a new id, the payment id, amount, reason, note, status `pending`, the admin who made the request, and the time.
  - Stored: the refund row and an audit entry "refund created". Both are saved when the transaction commits (is saved). Committing also releases the lock.
  - On failure: if the commit fails, both the refund row and the audit entry are undone. The admin sees an error and can submit again. The lock guarantees that no other refund could push the total above the captured amount in the meantime.

- [ ] **5. Call the provider's create-refund API**
  - Starts when: step 4 has committed. This call is made outside the transaction, so the lock is already released.
  - Data sent: the charge id from the payment, the amount in cents, and the refund id as the idempotency key. Each attempt has a timeout of 10 seconds.
  - Retries: if an attempt times out or gets a 5xx response, the server retries up to 3 more times (4 attempts in total), using the same idempotency key. Because the key is the same, a retry cannot create a duplicate refund.
  - Stored: when the provider responds with success, its refund id is saved on the refund row. The status stays `pending`, because success here only means the provider accepted the refund.
  - On failure: a 4xx response goes to step 6 as a rejection. A timeout or 5xx that still fails after all attempts goes to step 6 as an unknown outcome. If the server crashes after step 4 and before saving the provider's refund id, the refund stays `pending` with no provider id. Step 11 finds it using the refund id.

- [ ] **6. Handle provider errors**
  - **4xx (the provider rejected the refund)**: set the status to `failed`, and save the provider's message in the failure message field. Do not retry. The admin sees the message on the payment page. An audit entry records the status change.
  - **Timeout or 5xx after all attempts**: the outcome is unknown, so the status stays `pending`. The admin sees "Provider has not confirmed yet." Step 11 resolves it later.
  - **Success (2xx)**: nothing changes beyond step 5.

- [ ] **7. Webhook endpoint for `refund.succeeded` and `refund.failed`**
  - Starts when: the provider sends a signed message to our endpoint.
  - Checks, in order:
    1. **Signature**: the server computes the signature over the raw request body, using the provider's signing secret, and compares it with the one sent. A bad signature gets a 400 response. Nothing is stored.
    2. **Event id**: if this event id was already processed, the server returns 200 and ignores the event. Nothing else happens.
    3. **Refund lookup**: the server finds the refund that has this provider refund id. If none exists (for example, the webhook arrived before step 5 saved that id), the server returns a 5xx response, so the provider redelivers the event later.
  - Stored: nothing yet. The event id is recorded in step 8, in the same transaction as the status change.
  - On failure: if processing fails, the server returns a 5xx response, so the provider redelivers the event.

- [ ] **8. Update the refund status**
  - Starts when: step 7 has verified a new event.
  - Rules:
    - The status can only move from `pending` to `succeeded`, or from `pending` to `failed`. The update is a conditional update: it applies only if the row is still `pending` when it is written. This means a webhook and the reconciliation job cannot both change the same refund.
    - A refund that is already `succeeded` or `failed` is never changed by a later or repeated event. So duplicate and out-of-order events do no harm.
    - If an event does not fit the current status (for example, a `refund.failed` event for a refund that already succeeded), the status is not changed. The event id is still recorded, and the audit entry records the conflict.
  - Stored: the refund row (if the status changed), the processed event id, and an audit entry. These are saved in one transaction together with step 9.
  - On failure: the transaction is rolled back. Nothing changes, and the webhook returns a 5xx response so the provider redelivers the event.

- [ ] **9. Update the order status**
  - Starts when: step 8 moves a refund to `succeeded`. A refund moving to `failed`, or a conflicting event, does not change the order.
  - Rules: add up all succeeded refunds for the payment. Pending refunds are not counted.
    - If the total is 0, the order status does not change.
    - If the total is less than the captured amount, the order shows "Partially refunded".
    - If the total equals the captured amount, the order shows "Refunded".
  - Stored: the order status field and an audit entry, in the same transaction as step 8.
  - On failure: the same as step 8. Both changes are rolled back together, and the webhook returns a 5xx response.

- [ ] **10. Customer email**
  - Starts when: step 8 commits a move to `succeeded`, or step 11 applies one. No email is ever sent for a pending or failed refund.
  - Rules:
    1. The email job is queued after the commit, so the email is never sent for a change that was rolled back.
    2. Before sending, the worker claims the send with a conditional update. It sets the "customer emailed" field to the current time only if the field is empty. If the field is already set, the claim fails and nothing is sent. This means a second attempt cannot email the customer again.
    3. The worker sends the email.
    4. If the send succeeds, the claim stands and the audit entry is written.
  - Stored: the "customer emailed" time on the refund row, and an audit entry "email sent" written after the send. This audit entry is written outside the status transaction, because the send cannot be undone.
  - On failure: if the email provider fails, the server clears the "customer emailed" field, so the queue's retry can claim the send again. The queue retries after a delay. An email failure never changes the refund's status. If the server crashes after the claim and before the send, the customer is not emailed. We accept this: a missed email is possible, a duplicate is not.

- [ ] **11. Reconciliation job**
  - Starts when: a scheduled job runs every hour. A refund that is pending for 24 hours is checked at least once in that time, so no refund stays pending for 24 hours without a direct check with the provider. Webhooks alone are not relied on.
  - Data: the job finds every refund that is still `pending`. For each one, it asks the provider for the current status. It uses the provider refund id if one was saved. Otherwise it uses the refund's own id, which is the idempotency key.
  - Rules:
    - If the provider reports success or failure, the job applies the rules of step 8 (including the conditional update). If the result is success, step 9 runs, and then step 10.
    - If the provider has no record of the refund, the refund is marked `failed`, with a failure message saying the provider never received it.
    - If the provider still reports the refund as pending, nothing changes.
  - Stored: the "last checked" time on each refund the job checks, and an audit entry for each check.
  - On failure: if the provider cannot be reached, the refund is skipped. Its status does not change, and it is checked again on the next run.

- [ ] **12. Audit logging**
  - Starts when any of these happens:
    - a refund is requested (step 2)
    - a refund is created (step 4)
    - a provider error is handled (step 6)
    - a webhook or reconciliation check changes a status (steps 7 to 8, and 11)
    - the order status changes (step 9)
    - an email is sent (step 10)
    - a reconciliation check runs (step 11)
  - Data: each entry records the actor, the action, the refund id (empty for step 2), the payment id, the status before and after, the time, and any extra details.
  - Stored: the audit table. For database changes, each entry is saved in the same transaction as the change it records. Two steps are exceptions. Step 2 writes its entry in its own transaction, so rejected requests are still recorded. Step 10 writes its entry after the email is sent, because the send is outside the database.
  - On failure: if an audit entry cannot be written in a database transaction, that change is rolled back. A database change is never kept without its audit entry.