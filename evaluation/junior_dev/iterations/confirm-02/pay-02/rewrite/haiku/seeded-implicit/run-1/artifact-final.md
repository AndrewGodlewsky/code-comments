# Refunds plan

Admins issue full and partial refunds from our internal admin page. Our server calls the card provider's refund API, stores each refund, and waits for the provider's final result in a signed webhook. The order status is then updated from the refunds that actually succeeded.

Today, refunds happen in the provider's dashboard, so our database never learns about them. This plan keeps our own record of every refund.

## Terms

- **Payment**: a customer charge we already store. It has the provider's charge ID, the captured amount in cents, and a status.
- **Captured amount**: the money the provider has taken for a payment. Only captured payments can be refunded.
- **Refund**: one refund against a payment. Stored in a new refund table. Each refund has a status: pending, succeeded or failed.
- **Provider**: the card provider. Only our server calls its API.
- **Idempotency key**: a unique ID we send with each create-refund call. If the provider sees the same key again within 24 hours, it returns the original refund and creates no new one.
- **Webhook**: a message the provider sends to our server when a refund's final result is known. It is signed so we can check it came from the provider. It can arrive more than once, and out of order.
- **Audit entry**: a log row that records who did what, and when.
- **Reconciliation job**: a scheduled job that asks the provider for the status of refunds that have been pending too long.

## Rules that apply to every step

- Amounts are whole cents.
- The total of pending and succeeded refunds on a payment must never exceed its captured amount. Failed refunds do not count.
- Every refund request and every status change gets an audit entry (who, what, when).
- The browser never talks to the provider.
- A refund must not stay pending for more than 24 hours without our server checking its status with the provider directly. Webhooks alone are not enough.

## Steps

- [ ] **Step 1. Admin opens the payment page and fills in the refund form.**
  - Trigger: an admin opens a payment.
  - Does: the form asks for an amount in cents, a reason from a fixed list (duplicate, fraudulent, customer request, other), and an optional free-text note.
  - Stores: nothing yet.
  - On failure: none. Nothing is saved until the form is submitted.

- [ ] **Step 2. Server receives the request (POST /refunds).**
  - Trigger: the admin submits the form.
  - Does: the server checks that the admin has refund permission and that the payment is captured. Only then does the request continue. The server writes an audit entry for the request, whether it is accepted or rejected.
  - Stores: an audit entry.
  - On failure: no permission, or the payment is not captured, means the request is rejected with a message. The audit entry still records the request.

- [ ] **Step 3. Check the amount and create the refund record.**
  - Trigger: step 2 passed.
  - Does: in one database transaction, the server locks the payment row. The lock makes two refunds on the same payment wait for each other, so their totals cannot both pass the check. The server adds the pending and succeeded refunds for this payment, plus the new amount. If that total is more than the captured amount, the request is rejected. Otherwise the server saves a new refund with status **pending**, the amount, reason, note, the admin's ID and a new idempotency key. The key is saved now so every retry in step 4 reuses it.
  - Stores: the new refund row, in our database.
  - On failure: if the total is too high, the admin sees an error and nothing is saved. If the transaction fails, nothing is saved and nothing is sent to the provider.

- [ ] **Step 4. Server calls the provider to create the refund.**
  - Trigger: step 3 committed.
  - Does: the server sends the charge ID, the amount and the idempotency key to the provider. The call has a 10-second timeout.
    - If the provider accepts the call, the refund stays **pending**. "Accepted" only means the provider has the request. The final result comes later, in step 5. The server saves the provider's refund ID.
    - If the call times out, or the provider returns a 5xx, the server retries with the same idempotency key, up to 3 more times. That is at most 4 calls in total.
    - If the provider returns a 4xx, the provider has rejected the refund. The server marks it **failed**, does not retry, saves the provider's message and shows that message to the admin.
  - Stores: the refund row, updated with the provider's refund ID and any failure message. Each status change gets an audit entry.
  - On failure: if every retry times out or returns a 5xx, the refund stays **pending**. The reconciliation job in step 7 picks it up. The provider may have created it anyway, and the same key stops a second refund.

- [ ] **Step 5. Webhook reports the final result.**
  - Trigger: the provider sends `refund.succeeded` or `refund.failed`.
  - Does: the server checks the signature first. Then it finds the refund by the provider's refund ID.
    - If the refund is already **succeeded** or **failed**, the server ignores the event. This covers duplicates and late events.
    - If the refund is **pending**, the server sets its status to the event's result and writes an audit entry.
    - If the result is succeeded, the server sends the customer an email, but only if this refund has no "email sent" mark. It sets the mark when it sends the email, so each refund gets one email.
  - Stores: the refund status, the audit entry, and the "email sent" mark.
  - On failure: a bad signature is rejected, and nothing changes. If the email fails, see the open questions.

- [ ] **Step 6. Update the order status.**
  - Trigger: step 5 set a refund to succeeded.
  - Does: the server adds up only the succeeded refunds on the payment.
    - Nothing succeeded: the order does not change.
    - Some succeeded, less than the captured amount: the order shows **Partially refunded**.
    - Succeeded total equals the captured amount: the order shows **Refunded**.
  - Stores: the order status.
  - On failure: if the update fails, the refund stays succeeded and the order status is recalculated the next time a refund on this payment changes. Pending and failed refunds never change the order status.

- [ ] **Step 7. Reconciliation job checks old pending refunds.**
  - Trigger: a scheduled run.
  - Does: the job finds every refund that has been pending for more than 24 hours. For each one, it asks the provider for the current status and applies the same result as a webhook in step 5. It then runs step 6.
  - Stores: the refund status, audit entries, and the order status.
  - On failure: a refund that the provider cannot answer for stays pending, and the job tries again on its next run.

## What happens when things fail

| Where | What fails | What happens |
|---|---|---|
| Step 2 | No refund permission, or payment not captured | Request rejected. Audit entry still written. |
| Step 3 | Total would exceed captured amount | Admin sees an error. Nothing saved. |
| Step 3 | Database transaction fails | Nothing saved. Nothing sent to provider. |
| Step 4 | Timeout or 5xx | Retry with the same key, up to 3 times. |
| Step 4 | Timeout or 5xx on every try | Refund stays pending. Reconciliation checks it. |
| Step 4 | 4xx from provider | Refund marked failed. No retry. Admin sees the provider's message. |
| Step 5 | Bad webhook signature | Rejected. Nothing changes. |
| Step 5 | Duplicate or late webhook | Ignored, because the refund is already final. |
| Step 5 | Email fails | See open questions. |
| Step 7 | Provider cannot answer | Refund stays pending. Job retries on its next run. |

## Open questions

- The brief does not say what the admin sees while a refund is pending after all retries fail. This plan leaves it pending and shows it as pending.
- The brief does not set how often the reconciliation job runs. It must run often enough that no refund stays pending for more than 24 hours.
- The brief does not say what happens if the customer email fails. The plan does not yet decide whether to retry it.
- A webhook could arrive before step 4 has saved the provider's refund ID. The plan does not yet say how that case is matched.