# Refunds from the admin page: implementation plan

Today support staff refund customers in the card provider's dashboard, so our database never learns that a refund happened. This plan lets admins issue full and partial refunds from our admin page, and our server records each one. The admin's request only reserves the amount in our database. Background jobs then make the provider call and record its final result, because the provider can take days to confirm a refund and no database lock may be held while we wait.

## Terms

- **Provider**: the card payment company. Its API creates refunds and reports their status. It also posts webhooks to us.
- **Captured amount**: money taken from the customer for a payment, in cents (`captured_amount_cents`). All amounts are integers in cents.
- **Reserve**: save a refund as `pending`, so its amount counts toward the captured amount.
- **Idempotency key**: a unique string sent with each create call. If the provider gets the same key again within 24 hours, it returns the original refund instead of making a new one. We use the refund id.
- **Webhook**: a signed message the provider posts to us when a refund changes. It can arrive twice or out of order.
- **Row lock (`FOR UPDATE`)**: other transactions that want the same row wait until this one commits or rolls back.
- **Transaction**: database writes that save together or undo together.
- **Conditional update**: an update that changes a row only if a column still holds the value we read. The number of rows it changes tells us whether we won.
- **Claim**: a conditional update that gives one caller the right to make a provider call. Only the caller whose update changed one row may call.
- **Outbox**: a table of emails waiting to be sent. The row is written in the same transaction as the state change, and a worker sends it later.
- **Audit log**: a table that only receives new rows. Nothing is changed or deleted.
- **Terminal status**: `succeeded` or `failed`. A terminal refund never changes again.
- **applyRefundTransition(refund_id, to_status, source, event_id?)**: the only code that changes a refund's status. It runs inside the caller's transaction and allows a change only from `pending`. It writes an audit row. When the new status is `succeeded`, it also queues the customer email (one outbox row per refund) and recomputes the order status. It does not change provider fields or `last_status_check_at`. `source` records what caused the change: `provider_response`, `webhook` or `reconciliation`.
- **Order status**: the label on the payment, based on succeeded refunds only. If the succeeded sum is 0, the label does not change. If it is above 0 but below the captured amount, the label is "Partially refunded". If it equals the captured amount, the label is "Refunded". Pending and failed refunds are ignored. The label is stored in `payments.refund_status` in the same transaction as the refund change, so the two never disagree.
- **Reconciliation job**: a scheduled job that asks the provider for the status of pending refunds.
- **Backoff with jitter**: wait a little longer before each retry, plus a random part, so retries do not all land at once.

Assumptions (not in the brief): the `payments` table has `id`, `provider_charge_id`, `captured_amount_cents`, and `status`. New tables are `refunds`, `refund_webhook_events`, `audit_log` (append-only), and `email_outbox`. An existing permission check answers "has refund permission". Refund statuses are `pending`, `succeeded` and `failed`; only `pending` can change. The customer's email, the payment's currency and a payment reference come from existing customer and payment data (see open questions).

## How the main flow runs

Steps 1 to 4 happen in the admin's request, which then returns. Steps 5 to 8 are the background worker's provider calls. Step 9 (webhooks) and step 10 (a scheduled job) record the final result. Step 11 (email) follows success. Each step saves its state before the next one starts, so a crash leaves a row that a later step can find.

## Steps

1. [ ] **Admin opens the payment page**
   - Starts: an admin opens a payment in the internal admin page.
   - Data: the server loads `captured_amount_cents`, `status` and `remaining_cents`. `remaining_cents` is captured minus the sum of `amount_cents` over this payment's refunds with status `pending` or `succeeded`. It is for display only.
   - State: read only.
   - On failure: an unknown payment returns 404. Users without refund permission do not see the refund button; step 3 checks again. A payment that is not `captured` shows no refund form.

2. [ ] **Admin submits the refund form**
   - Starts: the admin clicks "Refund" and enters an amount (integer cents), a reason and an optional note. The reason is one of `duplicate`, `fraudulent`, `customer_request` or `other`.
   - Data: the browser creates a `refund_request_id` (UUID) when it draws the form and sends it with the submit. The browser posts only to `POST /admin/payments/:id/refunds` on our server. It never calls the provider.
   - State: none.
   - On failure: field errors show inline and nothing is sent. A double-click sends the same `refund_request_id`, which step 4 handles.

3. [ ] **Server checks and audits the request**
   - Starts: the POST from step 2.
   - Checks, on the server: the admin has refund permission (the UI check is not enough); the payment status is `captured`; the amount is an integer above zero; the reason is in the list; the note is within its length limit. The amount is not checked against the remaining balance here, because that check would race. Step 4 does it under a lock.
   - State: write an `audit_log` row for every request, accepted or rejected: actor, payment id, amount, reason, `refund_request_id`, outcome and timestamp.
   - On failure: a permission failure returns 403. A validation or status failure returns 422. Both are audited as rejected. No refund row is created and the provider is not called.

4. [ ] **Reserve the amount in one transaction, then answer the admin**
   - Starts: step 3 passed.
   - In one transaction:
     1. Lock the payment row: `SELECT ... FROM payments WHERE id = ? FOR UPDATE`. Concurrent refunds on this payment wait here.
     2. Sum `amount_cents` over this payment's refunds with status `pending` or `succeeded`. Failed refunds are left out, which releases their amount.
     3. If sum + requested amount > captured amount: audit the rejection, roll back and reject.
     4. Otherwise insert a `refunds` row: `id = refund_request_id`, `payment_id`, `amount_cents`, `reason`, `note`, `status = 'pending'`, `idempotency_key = id`, `provider_refund_id = NULL`, `attempts = 0`, `created_by`, `created_at`. The primary key makes a repeated submit do nothing, and the handler returns the existing refund's current state.
     5. Audit `refund.created` (from null, to pending). Commit.
   - After commit: the admin sees "Refund submitted, awaiting provider confirmation", with the refund id, amount and `pending` status. The browser does not wait for the provider.
   - Concurrency: a second admin refunding the same payment waits at the lock. Then it sees the first pending row in the sum and is rejected if the total would be too high.
   - Hand-off: the commit leaves a `pending` row with `attempts = 0`. The step 5 worker finds it within about a minute. If it never does, step 10 finds it, so no separate queue is needed.
   - On failure: a database error rolls back, so nothing is reserved, and the admin is asked to retry. The provider has not been called.

5. [ ] **First provider call**
   - Starts: the background worker, which checks once a minute for `pending` refunds with `attempts = 0` and no `provider_refund_id`. The call runs after step 4 commits, never while a row lock is held.
   - Claim: before each attempt, a short transaction runs a claim. It sets `attempts` to the value it read plus one, only if the refund is still `pending`, still has no `provider_refund_id`, and `attempts` still equals the value read. Only the caller whose update changed one row may call the provider. So two workers, or a worker and step 10, never both make a call. The claim commits before the HTTP call, so a crash after this point leaves a record. Each retry claims the same way.
   - Data sent (only our server sends it): provider charge id, `amount_cents`, idempotency key = `refunds.id`, and metadata with our refund id. Timeout: 10 seconds.
   - Outcomes: a 2xx goes to step 7. A timeout or 5xx goes to step 6. A 4xx goes to step 8. A failed claim means another caller owns the refund, so this caller stops.

6. [ ] **Retry timeouts and 5xx responses**
   - Starts: a timeout or 5xx from step 5, or from a reconciliation re-send in step 10.
   - Behaviour: retry up to 3 times, so 4 attempts in total, with backoff and jitter. Each attempt claims first (as in step 5), uses the same idempotency key and has a 10-second timeout. The same key means the provider returns the original refund if an earlier attempt created it. Store the last error in `provider_error`.
   - Outcomes: a 2xx on any attempt goes to step 7. A 4xx on any attempt goes to step 8.
   - All attempts fail: the refund stays `pending` with no `provider_refund_id`. It is not marked failed, because the provider may have created it. Audit `refund.submit_exhausted`. The admin sees "submitted, status being confirmed". Step 10 takes over.
   - Crash mid-retry: the row stays `pending` with `attempts` recorded, so step 10 picks it up.

7. [ ] **Record the provider's acceptance**
   - Starts: a 2xx from step 5, 6 or 10.
   - Data: in one short transaction, lock the refund row (`FOR UPDATE`), store `provider_refund_id` from the response if it is still empty, and audit `refund.submitted` with the provider id. Commit.
   - Status: the response means "accepted", so the status normally stays `pending`. If the response already says `succeeded`, call `applyRefundTransition(pending → succeeded, source = provider_response)` in the same transaction.
   - Webhooks: a webhook cannot match this refund until this commit, because step 9 looks up the id. If a webhook arrives during this write, it waits on the same row lock, so the two run one after the other.
   - On failure: a malformed 2xx is an unknown outcome, handled as in step 6. It is never marked failed.

8. [ ] **Handle a 4xx rejection**
   - Starts: a 4xx from step 5, 6 or 10.
   - Data: `provider_error` stores the provider's message.
   - State: `applyRefundTransition(pending → failed, source = provider_response)`. The amount is released automatically, because failed refunds are left out of step 4's sum. Audit with the provider's message.
   - No retries. No customer email.
   - Admin: the provider's message is shown on the refund list, escaped for display.
   - The order status does not change, because it depends only on succeeded refunds.

9. [ ] **Apply the final result from a signed webhook**
   - Starts: the provider posts `refund.succeeded` or `refund.failed` to `POST /webhooks/provider`. The event is assumed to carry the provider's refund id (see open questions).
   - Verify: check the signature over the raw request body with the webhook secret. A bad signature returns 400. A timestamp outside the provider's tolerance window is rejected.
   - Deduplicate: in the same transaction as the change, insert the event into `refund_webhook_events` with a unique `event_id`. A repeated `event_id` returns 200 and does nothing. Because the insert and the change commit together, a failed run does not count as seen.
   - Find: look up the refund by `provider_refund_id` and lock it with `FOR UPDATE`. If nothing matches, the webhook came before step 7 stored the id. Roll back and return 503, so the provider redelivers.
   - Apply:
     - Refund is `pending`: call `applyRefundTransition` with the event's status and `event_id`.
     - Refund is already terminal and the event agrees: no-op.
     - Refund is already terminal and the event conflicts: change nothing. Audit `conflicting_event` and raise an alert.
     - The only transition is out of `pending`, so the order in which the two event types arrive does not matter.
   - State: `applyRefundTransition` audits the change as `refund.status_changed` with `source = webhook` and `event_id`.
   - Response: commit, then return 200. If processing fails, return 500 so the provider retries.

10. [ ] **Reconciliation job checks pending refunds directly**
    - Starts: a scheduled job every 15 minutes. It covers refunds left by step 6, by crashes, and by webhooks that never arrive.
    - Selection: every `pending` refund, checked as follows:
      - With a `provider_refund_id`: when `now - coalesce(last_status_check_at, created_at) >= 1 hour`.
      - Without one, created less than 2 hours ago: on every run.
      - Without one, created 2 hours or more ago: on the hourly schedule above.
    - With a `provider_refund_id`: call the provider's refund-retrieve API. A `succeeded` answer calls `applyRefundTransition(→ succeeded, source = reconciliation)`. A `failed` answer calls `applyRefundTransition(→ failed, source = reconciliation)`. Any other answer leaves the refund pending. The transition is idempotent, so a repeat has no effect.
    - Without a `provider_refund_id`, created less than 2 hours ago: re-send the create call. Each re-send is one full sequence of up to 4 attempts, with the same claim and the same handling as steps 5 and 6, using the same key. The count in `attempts` keeps growing. A 2xx goes to step 7, which stores the id. This is safe because the provider returns the original refund for the same key within 24 hours. A 4xx goes to step 8. If every attempt fails, the refund stays pending and the next run tries again.
    - Without a `provider_refund_id`, created 2 hours or more ago: never re-send create, because that could make a duplicate. Look the refund up by our metadata refund id with the provider's search or list call (see open questions). If found, store its id as in step 7 and apply its status. If not found, leave it pending. The monitoring below escalates it.
    - Recording: after a check that got an answer (a retrieve, a create or a lookup), update `last_status_check_at`, whether or not the status changed. If the call itself fails, leave the row pending and do not update `last_status_check_at`. The next run retries.
    - Monitoring: alert if any pending refund has gone 20 hours without a check. Page on-call if any pending refund reaches 24 hours. This is the guarantee that no refund stays pending for more than 24 hours without a direct provider check.

11. [ ] **Send the customer email once, after success**
    - Starts: the email worker polls `email_outbox` for rows with `sent_at IS NULL`. The row was written inside `applyRefundTransition` when the refund became `succeeded`.
    - Data: the outbox row holds only the refund id and the type. When sending, the worker reads the customer email, the refund amount, the currency and the payment reference from the refund's payment and its customer. Only succeeded refunds get an email.
    - State: the row records `sent_at` and `attempts`. The unique (`refund_id`, `type`) constraint allows one row per refund.
    - On failure: a send error leaves the row unsent, and the worker retries with backoff. After a set number of attempts, alert. If the process crashes after sending but before `sent_at` is written, a duplicate is possible. Mitigation: pass the outbox id as the email provider's idempotency key, if supported (see open questions).

12. [ ] **The final outcome is recorded**
    - Starts: a refund reaches a terminal status, `succeeded` or `failed`, from step 7, 8, 9 or 10.
    - State: no extra write. The `refund.status_changed` audit row that `applyRefundTransition` writes for that change is the final record.
    - Admin page: the refund list shows the final status. The payment shows the recomputed order status.
    - Done when: every refund ends `succeeded` or `failed`; every request and status change has an audit row; a succeeded refund has exactly one email row queued or sent.

## What happens when things fail, across steps

- The provider is never called while the payment row lock is held.
- Every provider call (steps 5, 6 and 10) has a 10-second timeout and claims its attempt first.
- A refund is marked `failed` only when the provider rejects it (4xx). A timeout, a 5xx or a missing answer leaves it `pending`.
- Webhooks are never the only source of the final result. Step 10 checks every pending refund directly.

## Open questions for the owner

- **429 responses.** The brief says 4xx means rejected. A 429 is often temporary. Decide whether it should be retried like a 5xx.
- **Refunds with no provider id after 2 hours.** Step 10 looks them up by our metadata refund id. The brief does not say the provider can do this. If it cannot, decide what happens to a refund that stays pending with no id. Until then, its webhooks keep getting 503.
- **Webhook body.** The plan assumes each webhook carries the provider's refund id. Confirm that, and whether it also carries our refund id.
- **Customer data for the email.** Confirm that the customer's email and the payment's currency and reference exist in our data. The assumed `payments` columns do not include them.
- **Conflicting terminal events.** The plan keeps the first terminal state and alerts on a conflicting later event. Confirm the provider never legitimately moves `failed` to `succeeded`. If it can, reconciliation should decide.
- **Retrieve statuses.** The brief does not name the status values the retrieve API returns. Assumed: `succeeded` and `failed` are final, and anything else means still pending. Confirm.
- **4xx on a repeated key.** Step 8 assumes a 4xx on a retry means the refund was not created. Confirm with the provider.
- **Email idempotency.** Confirm whether the email provider accepts an idempotency key. Without one, a rare duplicate email is possible after a crash.
- **Timing of the 24-hour idempotency window.** The plan assumes the window starts at the first create call. Confirm this with the provider.