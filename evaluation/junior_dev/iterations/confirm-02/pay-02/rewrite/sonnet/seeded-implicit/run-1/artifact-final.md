# Refunds from the admin page

Support staff used to refund customers in the card provider's dashboard, so our database never learned about it. This plan lets admins issue full and partial refunds from our own admin page. Our server records each refund, asks the provider to make it, and then waits for the provider's later webhook (or our own status check) to learn the final result. The provider confirms a refund only after it has accepted it, sometimes days later, so each refund starts as pending and ends as succeeded or failed.

Today, we store payments with the provider's charge id, the captured amount and a status. There is no refund table.

## Terms

- **Captured payment**: a payment whose money the provider has actually collected. Only these can be refunded.
- **Refund record**: our own row for one refund attempt. It holds the payment, amount in cents, reason, note, idempotency key, status and provider refund id. Status is `pending`, `succeeded` or `failed`.
- **Idempotency key**: a unique value we send with the create-refund call. If the call is repeated with the same key within 24 hours, the provider returns the original refund instead of creating another one. We create the key once, when we create the refund record, and store it on that record.
- **Webhook**: a message the provider sends to our server when a refund's final result is known. It is either `refund.succeeded` or `refund.failed`, signed so we can check it came from the provider. It can arrive more than once and out of order.
- **Audit entry**: a log row saying who did what and when.
- **Reason**: one of duplicate, fraudulent, customer request or other. A free-text note is optional.

## Rules that apply to every step

- Amounts are in cents. A payment can have several partial refunds.
- The sum of `pending` and `succeeded` refunds on a payment must never exceed its captured amount. `failed` refunds do not count. This must hold when two admins refund the same payment at the same moment.
- Only our server talks to the provider. The browser never does.
- Every refund request and every status change writes an audit entry (who or what caused it, what changed, when).
- The order shows "Partially refunded" or "Refunded" based on `succeeded` refunds only.

## How it runs

1. **Admin opens a payment.** The payment page shows a refund form (amount, reason, optional note), but only to admins with refund permission, and only for captured payments. The browser sends the form to `POST /refunds` on our server.
2. **Server checks the request.** It confirms again that the user has refund permission, the payment is captured, the reason is on the list, and the amount is above zero. If any check fails, it returns an error to the admin and creates nothing.
3. **Server reserves the amount and creates the refund record.** In one database transaction it locks the payment row, so a second admin refunding the same payment waits. It adds up the payment's `pending` and `succeeded` refunds. If that sum plus the new amount exceeds the captured amount, it rejects the request and tells the admin how much is left. Otherwise it saves the refund record as `pending`, with its idempotency key, and writes the audit entry for the request. The refund record is stored in our database. The lock is what keeps two simultaneous refunds from going over the limit.
4. **Server calls the provider's create-refund API.** This happens after the transaction commits, so the lock is not held during a slow network call. It sends the charge id, amount and the stored idempotency key, with a 10-second timeout.
   - On a timeout or a 5xx, it retries up to 3 times with the same key. The key means the provider never creates two refunds. If all retries fail, the refund stays `pending` and step 8 settles it. The admin is told the request is still being processed.
   - On a 4xx, the provider has rejected the refund. We do not retry. We set the refund to `failed`, write an audit entry, and show the admin the provider's message. A failed refund stops counting toward the limit, so the amount becomes available again.
   - On success, the response only means "accepted". We store the provider's refund id on the refund record and leave it `pending`. The admin sees "Refund submitted".
5. **Provider sends a webhook.** Our webhook endpoint first checks the signature and rejects the message if it is not valid. It finds the refund record by the provider's refund id, then applies the result with the rules in step 6. It always replies with success once it has handled the message, including a repeat, so the provider stops resending.
6. **Server updates the refund status.** One function does this for both webhooks and the status check in step 8, so the two behave the same.
   - Only a `pending` refund can change. A refund that is already `succeeded` or `failed` is left alone, which makes repeated or out-of-order messages harmless. The result is `succeeded` or `failed`, as the provider reported.
   - Each change writes an audit entry (who or what caused it, the old and new status, when) in the same transaction as the change.
   - After a change to `succeeded`, it runs step 7. After a change to `failed`, nothing else happens: the amount is free again.
7. **Server updates the order and emails the customer.** This runs only when a refund has just become `succeeded`, so it happens once per refund. The server adds up the `succeeded` refunds on the payment. If the total is less than the captured amount, the order becomes "Partially refunded". If it equals the captured amount, the order becomes "Refunded". It then emails the customer. To make sure only one email goes out, the server marks the refund as emailed in the same transaction as the status change, and sends the email only if it was the one that set the mark. If the email fails to send, it is retried later, and it is never sent before the refund has succeeded.
8. **Reconciliation job.** A scheduled job runs regularly, for example every 15 minutes. It finds `pending` refunds older than some threshold, for example 12 hours, so none stays pending past 24 hours without a direct check. For each, it asks the provider for the refund's current status. If the refund has no provider refund id because step 4 never got a response, it repeats the create call with the stored idempotency key. The provider returns the original refund if it exists, or creates it if it does not. If a refund is more than 24 hours old, the key may have expired, so the job asks the provider for status by charge instead and flags the refund for a person to review if it cannot match one. The job then applies the result through step 6. If the provider call fails, the job tries again on its next run.

## What happens when things fail

| Where | Failure | Result |
|---|---|---|
| Step 2 | Missing permission, payment not captured, bad input | Error shown, nothing saved |
| Step 3 | Amount exceeds what is left | Request rejected, nothing saved |
| Step 3 | Two admins at once | The second waits for the lock, then is checked against the updated total |
| Step 4 | Timeout or 5xx after 3 retries | Refund stays `pending`, the job in step 8 settles it |
| Step 4 | 4xx | Refund marked `failed`, provider message shown |
| Step 5 | Bad signature | Message rejected, nothing changes |
| Step 5 or 6 | Duplicate or out-of-order webhook | Ignored if the refund is no longer `pending` |
| Step 7 | Email send fails | Retried later, still sent only once |
| Step 8 | Provider status call fails | Retried on the next run |

## Open questions

- How often the reconciliation job runs, and how old a `pending` refund must be before it is checked, are suggested values (every 15 minutes, 12 hours). They need confirming. The only fixed requirement is that no refund stays pending for more than 24 hours without a direct check.
- Whether the provider lets us look up a refund by idempotency key or by charge once the 24-hour key window has passed. The plan assumes a lookup by charge exists.
- Whether a webhook can arrive for a refund we have no record of, for example one made in the provider's dashboard. The plan ignores it and logs it.
