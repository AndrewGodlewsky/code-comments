# Plan: Refunds from the admin page

Steps are in the order they happen. Each step lists what starts it, what data moves, where state is stored, and what happens on failure.

## Overview

An admin submits a refund. We reserve the amount in our database, then a background worker asks the card provider to create the refund. The provider first answers "accepted". It reports the real result later through a webhook (a signed HTTP callback it sends to our server). A scheduled job also asks the provider directly, so a lost webhook cannot leave a refund pending forever. Only a refund that has actually succeeded changes the order status or emails the customer.

## Terms

- **Provider:** the card provider that processes refunds.
- **Provider charge id:** the id the provider gave us when the payment was captured. It is stored on the `payments` row.
- **Idempotency key:** a unique value we send with the create-refund call. If the provider receives the same key again within 24 hours, it returns the original refund instead of creating a new one.
- **Worker:** a background process that runs queued jobs, such as `submit_refund`.
- **Sweeper:** the scheduled job in step 10.
- **Final status:** `succeeded` or `failed`. A refund in a final status never changes again.
- **Amounts:** all amounts are integers in cents.

## Design decisions

- **New table `refunds`:**
  - `id`
  - `payment_id`
  - `amount_cents` (integer, > 0)
  - `reason` (enum: duplicate, fraudulent, customer_request, other)
  - `note` (nullable text)
  - `status` (`pending`, `succeeded`, `failed`)
  - `idempotency_key` (UUID, unique, generated once when the row is created and never changed)
  - `provider_refund_id` (nullable, unique)
  - `failure_message` (nullable)
  - `requested_by`
  - `created_at`
  - `updated_at`
  - `last_provider_check_at` (nullable)
  - `customer_emailed_at` (nullable)
- **New table `audit_log`** (append-only): `id`, `actor` (an admin id, or `system`, `webhook` or `sweeper`), `action`, `refund_id`, `payment_id`, `from_status`, `to_status`, `detail` (JSON), `at`.
- **New table `webhook_events`:** `provider_event_id` (unique), `type`, `received_at`, `processed_at` (nullable). It is used to drop duplicate deliveries.
- **Existing tables used:** `payments` (provider charge id, captured amount, status) and `orders`.
- **Status flow:** `pending` becomes `succeeded` or `failed`, and those two are final. A later event never changes a final status, whatever order events arrive in. If an event reports a final status that differs from the stored one, write an audit entry with the detail "conflict" and raise an alert. Do not overwrite the status.
- **Refundable total:** pending and succeeded refunds count toward the captured amount. Failed refunds do not. A `pending` refund counts from the moment its row is created. This is why the 24-hour check (step 10) is mandatory: a stuck refund would otherwise lock part of the payment's balance forever.
- **Order status:** computed from `SUM(amount_cents) WHERE status='succeeded'`. It is `Refunded` if the sum equals the captured amount, `Partially refunded` if the sum is above 0 and below the captured amount, and unchanged if the sum is 0. Pending refunds never affect it.

## Checklist

- [ ] **1. Admin opens the payment page**
  - **Starts:** the admin navigates to the payment in the admin page.
  - **Data:** the server checks the session and the `refund` permission. It then loads the payment (captured amount, status), its refunds, and the remaining refundable amount: `captured - SUM(amount) WHERE status IN ('pending','succeeded')`.
  - **State:** read only.
  - **Failure:** without the `refund` permission the Refund button is not rendered, and the refund endpoint (step 2) returns 403. A payment whose status is not `captured` shows no Refund button.
  - The displayed remaining amount is only a hint. Step 3 enforces the limit.

- [ ] **2. Admin submits the refund form**
  - **Starts:** the admin enters an amount in cents (or picks "full" for the remaining amount), picks a reason from the list, optionally adds a note, and submits.
  - **Data:** the browser sends `POST /admin/payments/{id}/refunds` with `amount_cents`, `reason` and `note`. The browser never contacts the provider.
  - **State:** none yet.
  - **Failure:** the server re-checks the session and permission (403 if missing). It then checks that the payment is `captured`, the amount is an integer > 0, the reason is in the list, and the note is within a maximum length. A validation error returns 400 or 422 with a message, and nothing is written.

- [ ] **3. Reserve the amount and create the refund row (one DB transaction)**
  - **Starts:** step 2 passed validation.
  - **Data:** in one transaction:
    1. Lock the payment row with `SELECT ... FROM payments WHERE id = ? FOR UPDATE`. This makes two admins refunding the same payment take turns.
    2. Compute `SUM(amount_cents)` over this payment's refunds with status `pending` or `succeeded`. If `sum + requested > captured_amount`, abort.
    3. Otherwise insert the `refunds` row with status `pending` and a newly generated `idempotency_key`.
    4. Write two audit entries: `refund_requested` (actor = admin, amount, reason, note) and a status entry `-> pending`.
  - **State:** `refunds` (pending) and `audit_log`. Both commit together or not at all.
  - **Failure:** if the limit would be exceeded, roll back, write nothing, and show the admin the current remaining amount. The second of two concurrent admins takes this path, because the first holds the lock until it commits. A DB error rolls back and shows a generic retryable error. No provider call has happened yet, so nothing needs cleaning up.

- [ ] **4. Enqueue the provider call**
  - **Starts:** the step 3 transaction commits.
  - **Data:** the job `submit_refund(refund_id)` is put on the background queue. The HTTP request returns 202 to the browser with the refund id and status `pending`, so the admin page does not wait on the provider.
  - **State:** the queue entry. The `refunds` row is the source of truth, so the job can always be rebuilt from it.
  - **Failure:** if the enqueue fails, or the server crashes between commit and enqueue, the row stays `pending` with no `provider_refund_id`. The sweeper (step 10) re-enqueues `submit_refund` for any such row older than 2 minutes.

- [ ] **5. Call the provider's create-refund API**
  - **Starts:** the worker runs `submit_refund`.
  - **Data:** the worker re-reads the row. If `provider_refund_id` is already set or the status is final, it stops. Otherwise it sends the create-refund request with the provider charge id, `amount_cents`, and the stored `idempotency_key` as the idempotency header. The call has a 10-second timeout. The key is always read from the row and never regenerated, so every retry reuses it.
  - **State:** nothing changes until the response is handled in step 6 or 7.
  - **Failure:** see steps 6 and 7.

- [ ] **6. Handle a timeout or a 5xx (retry)**
  - **Starts:** the call times out after 10 seconds, or the provider returns 5xx.
  - **Data:** retry with the same idempotency key, up to 3 retries (4 attempts in total), with backoff (for example 1s, 3s, 9s). If an earlier attempt did reach the provider, the key makes the provider return the original refund, so no duplicate is created.
  - **State:** one audit entry per failed attempt (`provider_call_retry`, attempt number, error). The refund stays `pending`.
  - **Failure:** if the 3rd retry also fails, the refund stays `pending` with no provider id, and the sweeper takes over (step 10). What the sweeper does depends on the refund's age, because the key's 24-hour window starts at the first attempt:
    - Under 24 hours old: it may resubmit with the same key.
    - Over 24 hours old: the key may have expired, so resubmitting could create a duplicate. The sweeper first asks the provider whether a refund exists for this charge and key, because an earlier request may have been accepted. If one exists, it records the provider id and status. If none exists, it marks the refund `failed` with the message "provider unreachable".
    - This way we never mark `failed` a refund the provider actually created.

- [ ] **7. Handle the provider's 2xx or 4xx response**
  - **Starts:** the provider answers.
  - **2xx (accepted):** in one transaction, store `provider_refund_id` on the row, keep the status `pending`, and write an audit entry (`provider_accepted`). The refund is not succeeded yet, because "accepted" is not the final result.
  - **4xx (rejected):** do not retry. In one transaction, set the status to `failed`, store the provider's message in `failure_message`, and write audit entries (`provider_rejected`, `pending -> failed`). The amount stops counting toward the limit, because failed refunds are excluded from the sum. The admin sees the provider's message (step 11). No customer email is sent.
  - **State:** `refunds` and `audit_log`.
  - **Failure:** if the DB write fails after a 2xx, the job retries the write. If it still fails, the sweeper recovers the provider id in step 10 by looking the refund up with the idempotency key.

- [ ] **8. Receive the provider's webhook**
  - **Starts:** the provider sends a `refund.succeeded` or `refund.failed` event to our webhook endpoint. This can be days after step 7. The provider may deliver an event more than once and out of order.
  - **Data:**
    1. The endpoint reads the raw body and verifies the signature (and the timestamp tolerance, if the provider signs a timestamp) before parsing anything. An invalid signature gets 400 and nothing is written.
    2. It inserts the event id into `webhook_events`. If that id already exists and has `processed_at` set, it returns 200 and does nothing (duplicate delivery).
    3. Otherwise it looks up the refund by `provider_refund_id` and goes to step 9.
  - **State:** `webhook_events`.
  - **Failure:**
    - If the refund id is unknown (for example the event arrived before step 7 stored the id), return a non-2xx status so the provider redelivers. The sweeper can also match the refund by idempotency key or metadata.
    - If processing fails, return 5xx so the provider redelivers. `processed_at` stays empty until the work finishes, and a redelivered event with no `processed_at` is processed again.

- [ ] **9. Apply the final status (shared by the webhook and the status check)**
  - **Starts:** step 8 found the refund, or step 10 got a final status from the provider.
  - **Data:** in one transaction:
    1. Lock the refund row (`FOR UPDATE`).
    2. If its status is already final, do nothing, except audit a "conflict" if the new status differs. This handles duplicate and out-of-order events.
    3. Otherwise set the status to `succeeded` or `failed` (with `failure_message` if provided) and write an audit entry (`status_changed`: actor = `webhook` or `sweeper`, from, to, event id).
    4. For `succeeded`, recompute the order status from succeeded refunds only (see Design decisions), update the order, and enqueue `send_refund_email(refund_id)` (step 12).
    5. For `failed`, nothing more is needed. The amount is released automatically because failed refunds are excluded from the limit.
    6. For a webhook, set `webhook_events.processed_at`.
  - **State:** `refunds`, `orders`, `audit_log`, `webhook_events`, and the email job. All of it commits together.
  - **Failure:** the transaction rolls back and the webhook returns 5xx, so the provider redelivers. Running the step again is safe, because the final-status check at the top makes it idempotent.

- [ ] **10. Scheduled check of stuck refunds (no refund stays pending over 24 hours unchecked)**
  - **Starts:** the sweeper runs every 15 minutes and selects:
    - `pending` refunds where `COALESCE(last_provider_check_at, created_at) < now() - interval '12 hours'`. Every pending refund is therefore checked at least every 12 hours, well inside the 24-hour limit.
    - `pending` refunds with no provider id that are older than 2 minutes (recovery for steps 4, 6 and 7).
  - **Data:** for each refund, it calls the provider's get-refund API (by `provider_refund_id`, or by idempotency key if there is no id), with the same 10-second timeout and retry rules as step 6. It sets `last_provider_check_at = now()` and writes an audit entry (`status_checked`). If the provider reports `succeeded` or `failed`, it runs step 9 with actor `sweeper`. If the refund is still pending, it leaves the status alone.
  - **State:** `refunds.last_provider_check_at`, `audit_log`, plus the effects of step 9.
  - **Failure:** if the provider cannot be reached, the job leaves `last_provider_check_at` unchanged, so the refund is picked up on the next run. It alerts if any refund is older than 20 hours with no successful check, and also alerts when the job itself fails. If the provider does not know the refund after the 24-hour window, handle it as described in step 6.

- [ ] **11. Show the outcome to the admin**
  - **Starts:** the admin's page loads, or polls every few seconds while a refund is pending on screen.
  - **Data:** the server returns each refund's status, amount, reason, `failure_message` and the order status. A rejected refund shows the provider's message.
  - **State:** read only.
  - **Failure:** a read error shows a retry message. It does not change any refund.

- [ ] **12. Email the customer once, after success**
  - **Starts:** the `send_refund_email(refund_id)` job that step 9 enqueued when it committed a change to `succeeded`.
  - **Data:** the worker runs `UPDATE refunds SET customer_emailed_at = now() WHERE id = ? AND status = 'succeeded' AND customer_emailed_at IS NULL` and sends the email only if one row was updated. The email contains the amount, the reason as shown to the customer, and the order reference. It is never sent for `pending` or `failed`.
  - **State:** `refunds.customer_emailed_at` and `audit_log` (`customer_emailed`).
  - **Failure:** if sending fails, the worker clears `customer_emailed_at` and retries with backoff. Because the claim is a conditional update, duplicate webhooks or a retried job cannot send two emails. One rare case remains: a crash after the mail was sent but before the timestamp was cleared or confirmed could send a second email. If that is not acceptable, pass a per-refund idempotency key to the mail provider.

- [ ] **13. Final outcome is recorded**
  - **Starts:** the refund has reached `succeeded` or `failed`.
  - **Data:** the end state is `refunds.status` (final), `provider_refund_id`, `failure_message`, the updated order status, and an audit trail covering the request, every retry and check, the status change, and the email.
  - **State:** `refunds`, `orders`, `audit_log`.
  - **Failure:** nothing is left to handle. A later conflicting event does not change the record. It is only audited and alerted on.

## Test checklist

- [ ] Two admins refund the same payment at once. The sum of pending and succeeded refunds stays within the captured amount, and the second request is rejected.
- [ ] A failed refund frees its amount for a new refund.
- [ ] A timeout followed by success sends the same idempotency key on every attempt and creates one refund at the provider.
- [ ] A 4xx marks the refund failed, makes no retry, and shows the provider's message.
- [ ] A duplicate webhook, a `succeeded` then `failed` conflict, and an out-of-order event each leave one correct final status and send exactly one email.
- [ ] A webhook with a bad signature is rejected and writes nothing.
- [ ] A refund with no webhook is resolved by the 12-hour check, and one pending past 20 hours without a check raises an alert.
- [ ] The order shows "Partially refunded" or "Refunded" from succeeded refunds only, never from pending ones.
- [ ] Every request and status change has an audit row.
