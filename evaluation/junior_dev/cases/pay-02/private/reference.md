# Plan: refunds from the admin page

**Where state lives**
- `payments` (ours, existing): provider charge id, `captured_amount`, status.
- `refunds` (ours, new): one row per refund. Fields: `id` (UUID), `payment_id`, `amount` (cents), `reason`, `note`, `admin_id`, `status` (`pending` → `succeeded` | `failed`), `provider_refund_id`, `failure_message`, timestamps.
- `audit_log` (ours): one entry per refund request and per status change (who, what, when).
- The provider keeps its own refund record. It is linked to ours by our refund `id`, which we send as both the idempotency key and `metadata.refund_id`.

**Remaining refundable** = `captured_amount` − the sum of `amount` over this payment's refunds in `pending` or `succeeded`. Failed refunds do not count.

## 1. Admin submits
- [ ] **1.1 Admin opens the payment page.** The server loads the payment and its refunds, then shows the captured amount, each refund with its status, and the remaining refundable amount. The Refund form appears only if the payment is `captured` and the admin has refund permission.
- [ ] **1.2 Admin submits the form** with the amount (cents, defaulting to the full remaining amount), a reason and an optional note. The browser POSTs to our server. It never calls the provider.
- [ ] **1.3 Server validates the input.** It re-checks the permission and the `captured` status, that the amount is > 0, and that the reason is on the list. If any check fails, it returns the error and stores nothing.

## 2. Reserve the amount (one database transaction)
- [ ] **2.1 Lock the payment row** (`SELECT … FOR UPDATE`). If a second admin refunds the same payment at the same moment, their request waits here until the first transaction commits.
- [ ] **2.2 Recompute the remaining refundable amount under the lock.** If the amount is more than what remains, roll back and show the admin the current remaining amount. Nothing is sent to the provider.
- [ ] **2.3 Insert the refund row with status `pending`.** Its `id` is the idempotency key for every provider call about this refund.
- [ ] **2.4 Write the audit entry** "refund requested" (admin, amount, reason, note), then **commit**. From now on, the pending amount counts against the remaining refundable amount.

## 3. Send to the provider (our server, after the commit)
- [ ] **3.1 Call create-refund** with the charge id, the amount, idempotency key = refund `id` and `metadata.refund_id` = refund `id`. The timeout is 10 s.
- [ ] **3.2 Handle the response.**
  - **2xx (accepted):** save `provider_refund_id` on the refund row. The status stays `pending`. Audit "accepted by provider".
  - **4xx (rejected):** set the status to `failed`, save the provider's message and audit. No retry. The amount goes back to the remaining refundable amount.
  - **Timeout or 5xx:** retry up to 3 times (backoff 1 s, 2 s, 4 s) with the **same** idempotency key, so the provider creates at most one refund. If every attempt fails, leave the status `pending` (the provider may have created the refund) and audit "provider unreachable". Step 5 settles it.
- [ ] **3.3 Respond to the admin.** The page shows the refund as **Pending** (or **Failed** with the provider's message), plus the updated remaining refundable amount. The customer is not emailed and the order status does not change yet.

## 4. Final result arrives by webhook
- [ ] **4.1 The provider POSTs `refund.succeeded` or `refund.failed`** to our webhook endpoint, anywhere from minutes to days later. Verify the signature. If it is invalid, return 400 and change nothing.
- [ ] **4.2 Find our refund** by `metadata.refund_id`. This works even if step 3.2 never saved `provider_refund_id`.
- [ ] **4.3 Apply the transition in one transaction.** Only `pending` → `succeeded` and `pending` → `failed` are allowed. If the row is already `succeeded` or `failed`, do nothing, which makes duplicate and out-of-order webhooks harmless. Audit the change. Return 200 for every valid webhook, including the no-ops, so the provider stops redelivering.
- [ ] **4.4 If the refund became `succeeded`:** recompute the order status from succeeded refunds only. If their total equals the captured amount, the order is **Refunded**; otherwise it is **Partially refunded**. Then queue the customer email with the refunded amount. This step runs only on the single `pending` → `succeeded` transition, so each refund produces exactly one email.
- [ ] **4.5 If the refund became `failed`:** the amount goes back to the remaining refundable amount and the admin page shows **Failed**. No customer email is sent and the order status does not change.

## 5. Reconciliation (does not depend on webhooks)
- [ ] **5.1 An hourly job selects refunds that have been `pending` for more than 1 hour.** This keeps every pending refund checked well within 24 hours.
- [ ] **5.2 Look up each one at the provider** by `metadata.refund_id`.
  - Provider says succeeded or failed: apply steps 4.3 to 4.5 exactly as if the webhook had arrived.
  - Provider has no record (the request never reached it): set the status to `failed` with "never reached provider", audit, and alert the finance channel. The admin can submit a new refund.
  - Provider says still pending: leave the refund as it is and check again next hour.
