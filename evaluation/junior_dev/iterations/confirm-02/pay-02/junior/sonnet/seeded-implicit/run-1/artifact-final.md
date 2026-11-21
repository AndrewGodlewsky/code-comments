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