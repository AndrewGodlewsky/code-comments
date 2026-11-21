# Refunds from the admin page: implementation plan

Assumptions made here, not stated in the brief: the existing `payments` table has `id`, `provider_charge_id`, `captured_amount_cents`, and `status`. New tables are `refunds`, `refund_webhook_events`, `audit_log` (append-only), and `email_outbox`. An existing permission check can answer "has refund permission". All state changes go through one function, `applyRefundTransition(refund_id, to_status, source, event_id?)`, which runs inside a database transaction and writes the audit row.

Allowed refund statuses: `pending`, `succeeded`, `failed`. `pending` is the only status that can change. `succeeded` and `failed` are terminal.

## Steps

1. [ ] **Admin opens the payment page**
   - Starts: an admin navigates to a payment in the internal admin page.
   - Data: the server loads the payment's `captured_amount_cents`, `status`, and `remaining_cents`. `remaining_cents` is captured minus the sum of `amount_cents` over refunds whose status is `pending` or `succeeded`. This value is for display only.
   - State: read only. Nothing is written.
   - On failure: unknown payment returns 404. A user without refund permission does not see the refund button. The server checks permission again at submit (step 3). A payment that is not captured shows no refund form.

2. [ ] **Admin fills in and submits the refund form**
   - Starts: the admin clicks "Refund" and enters amount (integer cents), reason (one of `duplicate`, `fraudulent`, `customer_request`, `other`), and an optional free-text note.
   - Data: the browser generates a `refund_request_id` (UUID) when the form is rendered and sends it with the submit. The browser posts only to our server endpoint `POST /admin/payments/:id/refunds`. It never calls the provider.
   - State: none yet.
   - On failure: field errors are shown inline and nothing is sent to the provider. A double-click sends the same `refund_request_id`, which step 4 uses to deduplicate.

3. [ ] **Server checks permission and input, and audits the request**
   - Starts: the POST from step 2.
   - Checks: the admin has refund permission (checked on the server, not only in the UI). The payment status is `captured`. The amount is an integer greater than zero. The reason is in the fixed list. The note is within a length limit. The amount is checked against the remaining balance in step 4, not here, because a check here would race.
   - State: an `audit_log` row is written for every request, accepted or rejected. It records actor, payment id, amount, reason, `refund_request_id`, outcome, and timestamp.
   - On failure: a permission failure returns 403. A validation or status failure returns 422. Both are audited as rejected. No refund row is created and the provider is not called.

4. [ ] **Reserve the amount in one transaction**
   - Starts: step 3 passed.
   - Data and state, in one transaction:
     - `SELECT ... FROM payments WHERE id = ? FOR UPDATE`. This serializes concurrent refunds on the same payment.
     - Sum `amount_cents` over refunds for this payment with status in (`pending`, `succeeded`). Failed refunds are excluded, so they release their amount.
     - If sum + requested amount > captured amount, reject. Audit the rejection and roll back.
     - Otherwise insert into `refunds`: `id = refund_request_id`, `payment_id`, `amount_cents`, `reason`, `note`, `status = 'pending'`, `idempotency_key = id`, `provider_refund_id = NULL`, `attempts = 0`, `created_by`, `created_at`. The primary key makes a repeated submit a no-op, and the handler returns the existing refund's current state.
     - Audit row: `refund.created`, with `from = null` and `to = pending`.
     - Commit.
   - Concurrency: if two admins refund the same payment at the same moment, the second transaction waits on the row lock. It then sees the first pending row in the sum and rejects if the total would exceed the captured amount.
   - On failure: a database error rolls back, so nothing is reserved, and the admin is asked to retry. The provider has not been called at this point.

5. [ ] **Call the provider's create-refund API (first attempt)**
   - Starts: step 4 has committed. The call is made after commit, never while the payment row lock is held.
   - Data sent from the server only: provider charge id, `amount_cents`, idempotency key = `refunds.id`, and metadata containing our refund id. The timeout is 10 seconds.
   - State: `attempts` is incremented and persisted before the call, so a crash leaves a record.
   - Outcomes:
     - 2xx: go to step 6.
     - Timeout or 5xx: go to step 5b.
     - 4xx: go to step 7.

5b. [ ] **Retry timeouts and 5xx responses**
   - Starts: a timeout or 5xx from step 5.
   - Behaviour: retry up to 3 times (4 attempts in total) with the same idempotency key, using backoff with jitter. Each attempt has a 10-second timeout. The same key means the provider returns the original refund if an earlier attempt actually created it.
   - State: `attempts` is updated on each try. `provider_error` holds the last error.
   - If a retry succeeds: continue as in step 6.
   - If all attempts fail: the refund stays `pending` with `provider_refund_id` unknown. It is not marked failed, because the provider may have created it. Audit `refund.submit_exhausted`. The admin sees "submitted, status being confirmed". Step 9 takes over.
   - Crash mid-retry: the row is still `pending` with `attempts` recorded, so step 9 picks it up.

6. [ ] **Record the provider's acceptance**
   - Starts: a 2xx response from step 5 or 5b.
   - Data: store `provider_refund_id`. The provider's immediate response means "accepted", so the status normally stays `pending`. If the response already says `succeeded`, call `applyRefundTransition` with source `provider_response` and continue to step 8's success path.
   - State: audit `refund.submitted` with the provider id.
   - Admin response: "Refund submitted, awaiting provider confirmation", with the refund id, amount, and `pending` status.
   - On failure: if the response is malformed but 2xx, treat it as step 5b (unknown outcome). Do not mark it failed.

7. [ ] **Handle a 4xx rejection**
   - Starts: a 4xx response from step 5.
   - Data: `provider_error` stores the provider's message.
   - State: `applyRefundTransition(pending -> failed, source = provider_response)`. The reservation is released automatically, because failed refunds are excluded from the sum in step 4. Audit with the provider's message.
   - No retries. No customer email.
   - Admin response: the provider's message is shown, escaped for display.
   - Order status is unchanged, because it depends only on succeeded refunds.

8. [ ] **Apply the final result from a signed webhook**
   - Starts: the provider posts `refund.succeeded` or `refund.failed` to `POST /webhooks/provider`.
   - Verification: check the signature over the raw request body with the webhook secret. Reject bad signatures with 400. Reject timestamps outside the provider's tolerance window.
   - Deduplication: inside the same transaction as the state change, insert into `refund_webhook_events` with `event_id` unique. A duplicate `event_id` returns 200 and does nothing. Because the insert and the change commit together, a failed processing run does not mark the event as seen.
   - Lookup and lock: find the refund by `provider_refund_id` and lock it with `FOR UPDATE`.
     - If no refund matches (the webhook arrived before step 6 stored the id): return 503 so the provider redelivers. Step 9 also covers this case.
   - Out-of-order and conflicts:
     - If the refund is `pending`, apply the event (`succeeded` or `failed`).
     - If the refund is already terminal and the event agrees, no-op.
     - If the refund is already terminal and the event conflicts, do not change it. Audit `conflicting_event` and raise an alert.
     - Because the only transition is out of `pending`, the order in which the two event types arrive does not matter.
   - State: audit `refund.status_changed` with `source = webhook` and `event_id`.
   - On `succeeded`: in the same transaction, insert into `email_outbox` (`refund_id`, `type = refund_succeeded`, unique on (`refund_id`, `type`)). Then run step 11.
   - On `failed`: the reservation is released automatically. No email.
   - Response: return 200 after commit. Return 500 if processing fails, so the provider retries.

9. [ ] **Reconciliation job checks pending refunds directly**
   - Starts: a scheduled job every 15 minutes. It also covers refunds left by step 5b and by crashes.
   - Selection: refunds with `status = 'pending'` where `now - coalesce(last_status_check_at, created_at) >= 1 hour`. Every pending refund is therefore checked directly with the provider well before its 24-hour mark, and webhooks are never the only source.
   - Data: call the provider's refund-retrieve API with `provider_refund_id`. Update `last_status_check_at` whether or not the status changed.
   - State: the returned status goes through `applyRefundTransition` with `source = reconciliation`. It is idempotent, so a repeat has no effect.
   - Refunds with no `provider_refund_id`: re-send create with the same key only while `created_at` is under 2 hours old, which is well inside the provider's 24-hour key window. After that, look up the refund by our metadata. If that is not possible, escalate (see open questions). Never re-send create after the window, because that could create a duplicate.
   - On failure: if the provider's retrieve call fails, leave the row `pending` and do not update `last_status_check_at`. The next run retries.
   - Monitoring: alert if any pending refund is older than 20 hours without a check. Page on-call if any pending refund reaches 24 hours. This is the guarantee that no refund stays pending for more than 24 hours without a direct provider check.

10. [ ] **Send the customer email, once, after success**
    - Starts: the outbox worker polls `email_outbox` for rows where `sent_at IS NULL`.
    - Data: refund id, customer email, refund amount, currency, and payment reference. Sent only for `succeeded` refunds.
    - State: `sent_at` and `attempts` are recorded on the row. The unique constraint on (`refund_id`, `type`) guarantees one row per refund.
    - On failure: a send error leaves the row unsent, and the worker retries with backoff. After a set number of attempts, alert. If the process crashes after sending but before `sent_at` is written, a duplicate is possible. Mitigate by passing the outbox id as the email provider's idempotency key, if supported (see open questions).

11. [ ] **Recompute the order status from succeeded refunds**
    - Starts: any transition to `succeeded`, inside the transaction from step 8 or step 9.
    - Rule: `succeeded_sum = 0` leaves the status unchanged. `0 < succeeded_sum < captured` sets "Partially refunded". `succeeded_sum = captured` sets "Refunded". Pending and failed refunds are ignored.
    - State: either recompute on read, or store `payments.refund_status` in the same transaction. Storing it in the same transaction keeps the status and the refund row consistent.
    - On failure: the transaction rolls back together with the refund change, so the two never disagree.

12. [ ] **Record the final outcome and close**
    - Starts: the refund reaches a terminal state, either `succeeded` (from step 8 or 9) or `failed` (from step 7 or 8 or 9).
    - State: write a final audit row `refund.final` with the final status, the payment's new succeeded total, and the email outbox state if relevant.
    - Admin page: the refund list shows the final status. The order shows the recomputed status.
    - Done: every refund ends in `succeeded` or `failed`. Every request and status change has an audit row. A succeeded refund has exactly one customer email queued or sent.

## Open questions for the owner

- **429 responses.** The brief says 4xx means rejected. Rate-limit responses (429) are often temporary. Decide whether 429 should be retried like a 5xx.
- **Refunds with no provider id after the window.** If the create call never reached the provider, the plan needs a way to confirm that. This depends on whether the provider supports lookup by our metadata. If it does not, decide what happens to a refund that stays pending with no provider id.
- **Conflicting terminal events.** The plan keeps the first terminal state and alerts on a conflicting later event. Confirm the provider never legitimately moves `failed` to `succeeded`. If it can, the reconciliation check should decide.
- **Email idempotency.** Confirm whether the email provider accepts an idempotency key. Without one, a rare duplicate email is possible after a crash.
- **Timing of the 24-hour idempotency window.** The plan assumes the window starts at the first create call. Confirm this with the provider.
