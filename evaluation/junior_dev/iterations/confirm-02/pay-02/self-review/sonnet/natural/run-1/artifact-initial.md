# Plan: Refunds from the admin page

Steps are in the order they happen. Each step lists its trigger, the data that moves, where state is stored, and what happens on failure.

## Design decisions

- **New table `refunds`:** `id`, `payment_id`, `amount_cents` (integer, > 0), `reason` (enum: duplicate, fraudulent, customer_request, other), `note` (nullable text), `status` (`pending`, `succeeded`, `failed`), `idempotency_key` (UUID, unique, created once with the row), `provider_refund_id` (nullable, unique), `failure_message` (nullable), `requested_by`, `created_at`, `updated_at`, `last_provider_check_at`, `customer_emailed_at` (nullable).
- **New table `audit_log`:** `id`, `actor` (admin id, or `system`/`webhook`/`reconciler`), `action`, `refund_id`, `payment_id`, `from_status`, `to_status`, `detail` (JSON), `at`. It is append-only.
- **New table `webhook_events`:** `provider_event_id` (unique), `type`, `received_at`, `processed_at`. It is used to drop duplicate deliveries.
- **Status flow:** `pending` goes to `succeeded` or `failed`, and those two are final. A final status is never changed by a later event, whatever order events arrive in. If a final event conflicts with the stored final status, write an audit entry with the detail "conflict" and alert on it. Do not overwrite the status.
- **Pending total:** `pending` counts toward the refundable total from the moment the row is created. This is why the 24-hour check (step 10) is mandatory. A stuck refund would otherwise lock the payment's balance.
- **Order status:** computed from `SUM(amount_cents) WHERE status='succeeded'`. It is `Refunded` if the sum equals the captured amount, `Partially refunded` if the sum is above 0 and below the captured amount, and unchanged if the sum is 0. Pending refunds never affect it.

## Checklist

- [ ] **1. Admin opens the payment page**
  - **Starts:** admin navigates to the payment in the admin page.
  - **Data:** server checks the session and the `refund` permission, then loads the payment (captured amount, status), its refunds, and the remaining refundable amount (`captured - SUM(amount) WHERE status IN ('pending','succeeded')`).
  - **State:** read only.
  - **Failure:** no `refund` permission means the Refund button is not rendered and the refund endpoint (step 2) returns 403. A payment whose status is not `captured` shows no Refund button.
  - The displayed remaining amount is a hint only. Step 3 enforces the limit.

- [ ] **2. Admin submits the refund form**
  - **Starts:** admin enters an amount in cents (or picks "full" for the remaining amount), picks a reason from the list, optionally adds a note, and submits.
  - **Data:** browser sends `POST /admin/payments/{id}/refunds` with `amount_cents`, `reason`, `note`. The browser never contacts the provider.
  - **State:** none yet.
  - **Failure:** server re-checks the session and the permission (403 if missing), validates that the payment is `captured`, the amount is an integer > 0 and the reason is in the list, and truncates or rejects an over-long note. Validation errors return 400 or 422 with a message. Nothing is written.

- [ ] **3. Reserve the amount and create the refund row (one DB transaction)**
  - **Starts:** step 2 passed validation.
  - **Data:** in one transaction, `SELECT ... FROM payments WHERE id = ? FOR UPDATE` (this serializes two admins on the same payment). Then recompute `SUM(amount_cents)` over this payment's refunds with status `pending` or `succeeded`. If `sum + requested > captured_amount`, abort. Otherwise insert the `refunds` row with status `pending` and a freshly generated `idempotency_key`. In the same transaction, write the audit entry (`refund_requested`: actor = admin, amount, reason, note) and an audit entry for `-> pending`.
  - **State:** `refunds` (pending), `audit_log`. Both commit together or not at all.
  - **Failure:** if the limit would be exceeded, roll back, write nothing, and show the admin the current remaining amount. The second of two concurrent admins hits this path because the first holds the row lock until commit. A DB error rolls back and shows a generic retryable error. No provider call has happened, so there is nothing to clean up.

- [ ] **4. Enqueue the provider call**
  - **Starts:** the transaction in step 3 commits.
  - **Data:** a job `submit_refund(refund_id)` is put on the background queue. The HTTP request returns 202 to the browser with the refund id and status `pending`, so the admin page does not wait on the provider.
  - **State:** the queue entry. The `refunds` row is the source of truth, so the job can be rebuilt from it. A sweeper (step 10) also picks up any `pending` row with no `provider_refund_id` older than 2 minutes, which covers a crash between commit and enqueue.
  - **Failure:** if the enqueue fails, the row stays `pending` with no provider id, and the sweeper submits it later.

- [ ] **5. Call the provider's create-refund API**
  - **Starts:** the worker runs `submit_refund`.
  - **Data:** the worker re-reads the row. If `provider_refund_id` is already set, or the status is final, it stops. Otherwise it sends the create-refund request to the provider with the payment's provider charge id, `amount_cents`, and the stored `idempotency_key` as the idempotency header. The call has a 10-second timeout. The key is read from the row and never regenerated, so every retry reuses it.
  - **State:** none changes until the response is handled in step 6 or 7.
  - **Failure:** see steps 6 and 7.

- [ ] **6. Handle a timeout or a 5xx (retry)**
  - **Starts:** the call times out after 10 seconds, or the provider returns 5xx.
  - **Data:** retry with the same idempotency key, up to 3 retries (4 attempts in total), with backoff (for example 1s, 3s, 9s). If the original attempt did reach the provider, the key makes the provider return the original refund, so no duplicate refund is created.
  - **State:** audit entry per failed attempt (`provider_call_retry`, attempt number, error). The refund stays `pending`.
  - **Failure:** after the 3rd retry also fails, the refund stays `pending` with no provider id. The key's 24-hour idempotency window starts from the first attempt, so the sweeper (step 10) may resubmit with the same key only while the refund is under 24 hours old. It marks the refund `failed` with the message "provider unreachable" if it is older than 24 hours and the provider has no record of it. In that case it first asks the provider whether a refund exists for this charge and key, because the original request may have been accepted. This makes sure we never mark `failed` a refund the provider actually created.

- [ ] **7. Handle the provider's 2xx or 4xx response**
  - **Starts:** the provider answers.
  - **2xx (accepted):** in one transaction, store `provider_refund_id` on the row, keep the status `pending`, and write an audit entry (`provider_accepted`). The refund is not succeeded yet, because "accepted" is not the final result.
  - **4xx (rejected):** do not retry. In one transaction set the status to `failed`, store the provider's message in `failure_message`, and write the audit entries (`provider_rejected`, `pending -> failed`). The amount no longer counts toward the cap, because failed refunds are excluded from the sum. Show the admin the provider's message (step 11). No customer email is sent.
  - **State:** `refunds`, `audit_log`.
  - **Failure:** if the DB write fails after a 2xx, the job retries the write. If it still fails, the sweeper reconciles with the provider in step 10 using the idempotency key, so the provider id is recovered.

- [ ] **8. Receive the provider's webhook**
  - **Starts:** the provider sends a `refund.succeeded` or `refund.failed` event to our webhook endpoint, days later in some cases.
  - **Data:** the endpoint reads the raw body and verifies the signature (and the timestamp tolerance, if the provider signs one) before any parsing. It rejects an invalid signature with 400 and writes nothing. It then inserts the event id into `webhook_events`, and if that id already exists it returns 200 and does nothing (duplicate delivery). Otherwise it looks up the refund by `provider_refund_id`.
  - **State:** `webhook_events`.
  - **Failure:** an unknown refund id (for example, the event arrives before step 7 stored the id) returns a non-2xx status so the provider redelivers, and the sweeper can also match on the idempotency key or metadata. A processing error returns 5xx so the provider redelivers, and the `webhook_events.processed_at` stays empty until the work finishes. A redelivery of an event that has no `processed_at` is processed again.

- [ ] **9. Apply the final status (shared by the webhook and the status check)**
  - **Starts:** step 8 found the refund, or step 10 got a final status from the provider.
  - **Data:** in one transaction, lock the refund row (`FOR UPDATE`). If its status is already final, do nothing except audit a conflict if the new status differs (this handles duplicates and out-of-order events). Otherwise set the status to `succeeded` or `failed` (with `failure_message` if provided), then write an audit entry (`status_changed`, actor = `webhook` or `reconciler`, from, to, event id). For `succeeded`, recompute the order status from succeeded refunds only (see Design decisions) and update the order. For `failed`, the amount is released automatically because failed refunds are excluded from the cap. Finally set `webhook_events.processed_at`.
  - **State:** `refunds`, `orders`, `audit_log`, `webhook_events`. All in one transaction.
  - **Failure:** the transaction rolls back and the webhook returns 5xx, so the provider redelivers. The step is safe to run again, because the status check at the top makes it idempotent.

- [ ] **10. Scheduled check of stuck refunds (no refund stays pending over 24 hours unchecked)**
  - **Starts:** a scheduled job runs every 15 minutes and selects `pending` refunds where `COALESCE(last_provider_check_at, created_at) < now() - interval '12 hours'` (so every pending refund is checked at least every 12 hours, well inside the 24-hour limit). It also selects `pending` refunds with no provider id older than 2 minutes (step 4 and step 6 recovery).
  - **Data:** for each refund, it calls the provider's get-refund API (by `provider_refund_id`, or by idempotency key if there is no id), with the same 10-second timeout and the same retry rules as step 6. It sets `last_provider_check_at = now()` and writes an audit entry (`status_checked`). If the provider reports `succeeded` or `failed`, it runs step 9 with actor `reconciler`. If still pending, it leaves the row alone.
  - **State:** `refunds.last_provider_check_at`, `audit_log`, plus step 9 effects.
  - **Failure:** if the provider cannot be reached, the job leaves `last_provider_check_at` unchanged, so the row is picked up on the next run, and it alerts if any refund is older than 20 hours with no successful check. Alert on job failures too. A refund the provider says it does not know, after the 24-hour window, is handled as in step 6.

- [ ] **11. Show the outcome to the admin**
  - **Starts:** the admin's page loads or polls (every few seconds while a refund is pending on screen).
  - **Data:** server returns each refund's status, amount, reason, `failure_message` and the order status. A rejected refund shows the provider's message.
  - **State:** read only.
  - **Failure:** a read error shows a retry message. It does not change any refund.

- [ ] **12. Email the customer once, after success**
  - **Starts:** step 9 committed a change to `succeeded`.
  - **Data:** in the same transaction as step 9, enqueue `send_refund_email(refund_id)`. The worker runs `UPDATE refunds SET customer_emailed_at = now() WHERE id = ? AND status = 'succeeded' AND customer_emailed_at IS NULL` and sends the email only if one row was updated. Content: amount, reason shown to the customer, order reference. It never emails for `pending` or `failed`.
  - **State:** `refunds.customer_emailed_at`, `audit_log` (`customer_emailed`).
  - **Failure:** if sending fails, the worker clears `customer_emailed_at` (or sets it only after the mail provider accepts the message) and retries with backoff. Because the claim is a conditional update, duplicate webhooks or a retried job cannot send two emails. Accept that a crash between a successful send and the stored timestamp could produce a rare duplicate. If that is not acceptable, pass a per-refund idempotency key to the mail provider.

- [ ] **13. Final outcome is recorded**
  - **Starts:** the refund has reached `succeeded` or `failed`.
  - **Data:** the end state is `refunds.status` (final), `provider_refund_id`, `failure_message`, the updated order status, and an audit trail containing the request, every retry and check, the status change, and the email.
  - **State:** `refunds`, `orders`, `audit_log`.
  - **Failure:** none left to handle. A later conflicting event does not change the record and is only audited and alerted on.

## Test checklist

- [ ] Two admins refund the same payment at once and the sum of pending and succeeded stays within the captured amount, with the second request rejected.
- [ ] A failed refund frees its amount for a new refund.
- [ ] A timeout then success sends the same idempotency key on every attempt and creates one refund at the provider.
- [ ] A 4xx marks the refund failed, makes no retry, and shows the provider's message.
- [ ] A duplicate webhook, a `succeeded` then `failed` conflict, and an out-of-order event leave one correct final status, and send exactly one email.
- [ ] A webhook with a bad signature is rejected and writes nothing.
- [ ] A refund with no webhook is resolved by the 12-hour check, and one pending past 20 hours without a check raises an alert.
- [ ] The order shows "Partially refunded" or "Refunded" from succeeded refunds only, never from pending ones.
- [ ] Every request and status change has an audit row.
