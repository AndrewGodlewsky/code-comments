# Plan: refunds from the admin page

## Shared definitions

**Refund states**

- `queued`: saved in our database, amount reserved, provider has not yet accepted it.
- `pending`: provider accepted the create call and returned a provider refund id. The final result is not known.
- `succeeded`: terminal. Provider confirmed the money moved.
- `failed`: terminal. Provider rejected the refund (4xx), or the provider later reported a failure.
- `needs_review`: not terminal. Our system could not confirm with the provider within 23 hours. An admin must resolve it.

Allowed transitions are `queued -> pending`, `queued -> failed`, `queued -> succeeded`, `pending -> succeeded`, `pending -> failed`, and `queued or pending -> needs_review`. `succeeded` and `failed` never change back.

**Reserved amount:** the sum of `amount_cents` over refunds on a payment whose state is `queued`, `pending`, `needs_review` or `succeeded`. `failed` refunds are excluded.

**Tables**

- `payments` (existing): charge id, captured amount in cents, status. The order status is derived from refunds.
- `refunds`: `id`, `payment_id`, `amount_cents`, `reason` (enum), `note`, `status`, `provider_refund_id` (nullable), `idempotency_key` (unique, server-generated UUID), `request_token` (unique, from the form), `attempts`, `last_attempt_at`, `last_error`, `failure_message` (provider text, shown to admins), `last_provider_check_at`, `created_by`, `created_at`, `updated_at`.
- `refund_webhook_events`: `provider_event_id` (unique), `type`, `refund_provider_id`, `raw_payload`, `received_at`, `processed_at`.
- `audit_log` (append-only): `actor` (admin id, `system:submitter`, `system:webhook`, `system:reconciler`), `action`, `payment_id`, `refund_id`, `from_status`, `to_status`, `details` (JSON), `created_at`.
- `email_outbox`: `refund_id`, `kind`, `status`, `attempts`, `sent_at`. Unique on (`refund_id`, `kind`).

---

## Checklist: steps in order

- [ ] **1. Admin opens the payment page**
  - Starts: an admin opens a payment in the internal admin page.
  - Data: payment id, captured amount, payment status, refund list, and the reserved total, all computed on the server. The order status is derived from succeeded refunds only.
  - Stored: read-only from `payments` and `refunds`. Nothing is written.
  - On failure: if the admin lacks refund permission, the refund button is hidden and every refund endpoint still returns 403. If the payment is not `captured`, the button is disabled with the reason shown. A read error shows an error page and writes nothing.

- [ ] **2. Admin fills in the refund form**
  - Starts: the admin clicks Refund.
  - Data: amount in integer cents, reason (one of duplicate, fraudulent, customer request, other), optional note, and a `request_token` generated when the form is rendered.
  - Stored: only in the browser. The browser sends the form to our server and never calls the provider.
  - On failure: client-side validation is a convenience only. The server checks everything again in step 3.

- [ ] **3. Server authorises and validates the request**
  - Starts: `POST /payments/{id}/refunds`.
  - Data: session identity, permission, payment status, amount, reason, note length cap, and `request_token` presence.
  - Stored: any rejection writes an `audit_log` row (`refund.request_rejected`, with the reason). A valid request continues to step 4.
  - On failure: return 403 for permission, 422 for invalid input or a non-captured payment. No refund row is created.

- [ ] **4. Reserve the amount in one database transaction**
  - Starts: step 3 passed.
  - Data: payment id, amount, reason, note, admin id, `request_token`.
  - Steps inside `BEGIN ... COMMIT`:
    1. `SELECT ... FROM payments WHERE id = ? FOR UPDATE`. This serialises two admins refunding the same payment.
    2. Sum the reserved amount (see definitions).
    3. If reserved + requested amount is greater than the captured amount, roll back, write a rejected audit row, and return 409 with the remaining refundable amount.
    4. Check `request_token`. If a row already exists for it, return that row and do not insert again. This handles double-clicks.
    5. Insert the `refunds` row with status `queued`, a new server-generated `idempotency_key`, and `attempts = 0`. The key is stored here, before any provider call, so every retry reuses it.
    6. Insert the audit row `refund.requested`, which includes the key.
  - Stored: `refunds`, `audit_log`, both in one transaction.
  - On failure: any database error rolls back, so nothing is reserved. The admin sees a retry message. A deadlock or serialisation error is retried once.

- [ ] **5. Hand the refund to the submission job**
  - Starts: the transaction in step 4 committed.
  - Data: refund id only.
  - Stored: a durable job queue entry. If enqueueing fails, the sweeper in step 9 will find the `queued` row.
  - Response: the admin gets 202 with the refund id and status `queued`. The page shows "Submitting" and checks again later (step 8).
  - On failure: enqueue errors are covered by step 9. The HTTP request does not wait for the provider, so an admin does not wait up to 43 seconds on the retry schedule.

- [ ] **6. Submission job calls the provider's create-refund**
  - Starts: the job runs for a refund id.
  - Data sent to the provider: the charge id from `payments`, `amount_cents`, the `idempotency_key` header, and metadata with our refund id and reason. The free-text note is not sent.
  - Timeout: 10 seconds per attempt.
  - Stored: before each attempt, increment `attempts` and set `last_attempt_at`, so a crash mid-call leaves a visible record.
  - On failure: handled in step 7.

- [ ] **7. Interpret the provider's response**
  - Starts: the create call returns or fails.
  - **2xx (accepted):** store `provider_refund_id` and set `last_provider_check_at`. Transition `queued -> pending`, but only if the row is still `queued`, so a webhook that has already moved it is not overwritten. Write `refund.pending` to the audit log.
  - **4xx (rejected):** transition `queued -> failed` and store the provider's message in `failure_message`. Write `refund.failed` to the audit log. Do not retry. The admin sees the message (step 8). Failed refunds stop counting toward the reserved total.
  - **Timeout, 5xx or network error:** retry with the same `idempotency_key`, with backoff of 1, 2 and 4 seconds. That is at most 3 retries, so 4 attempts in total. Within 24 hours the provider returns the original refund rather than creating a second one.
  - **Retries exhausted:** leave the row `queued`, record `last_error`, and do not mark it failed. The provider may already have created the refund. Hand over to the sweeper in step 9.
  - On failure: the state is always in the database, so a crash in any branch is recovered by step 9.

- [ ] **8. Admin sees the result**
  - Starts: the admin's page polls, or the admin reloads it.
  - Data: refund status, `failure_message` for failed refunds, and the order status.
  - Stored: read-only.
  - On failure: closing the page loses nothing. The state is in the database.

- [ ] **9. Sweeper resumes stuck `queued` refunds**
  - Starts: a scheduled job every 5 minutes. It selects `queued` rows whose `last_attempt_at` is more than 5 minutes ago and whose `created_at` is less than 23 hours ago.
  - Action: resubmit through step 6 with the same stored key. The provider returns the original refund if an earlier attempt created one.
  - Past 23 hours: if the provider has still not given a clear answer, set the status to `needs_review`, write an audit row, and alert admins. The amount stays reserved until a person resolves it. An admin with refund permission can then re-check with the provider or mark the refund failed, and that action is audited.
  - On failure: if the sweeper stops running, alert on the age of the oldest `queued` row.

- [ ] **10. Provider webhook arrives (`refund.succeeded` or `refund.failed`)**
  - Starts: the provider posts to our webhook endpoint. The browser is not involved.
  - Verify: check the signature over the raw request body with the webhook secret. Reject invalid signatures with 401 and write no state. Reject timestamps outside a 5-minute tolerance to limit replay.
  - Dedupe: insert the `provider_event_id` into `refund_webhook_events` with a unique constraint. A duplicate id returns 200 and does nothing else.
  - Match: find the refund by `provider_refund_id`. If no refund matches yet (the webhook beat step 7), keep the event with `processed_at` null. Step 12 processes it later.
  - Respond: return 2xx only after the event row is committed. Return 500 if the database write fails, so the provider retries.
  - On failure: the provider's retry plus the dedupe key make this safe.

- [ ] **11. Apply the status change (one shared transition function)**
  - Starts: called from step 7 (create response), step 10 (webhook) or step 12 (direct check).
  - Rules:
    - Apply the change with a conditional update (`UPDATE ... WHERE status = expected`), so only allowed transitions happen.
    - Out-of-order or duplicate events, such as a `pending` update after `succeeded`, make no change and are logged.
    - A conflicting terminal event, such as `failed` after `succeeded`, does not flip the state. The function triggers a direct check (step 12) and raises an alert.
  - In one transaction:
    1. Update the refund's status, timestamps and `provider_refund_id`.
    2. Write an audit row with actor, from and to status, and the provider event id or check id.
    3. If the new status is `succeeded`, insert an `email_outbox` row with `kind = refund_succeeded`. The unique key on (`refund_id`, `kind`) means exactly one email is ever queued.
  - Order status: recalculated from `succeeded` refunds only. It becomes "Partially refunded" when the succeeded total is greater than 0 and less than captured, and "Refunded" when it equals captured.
  - On failure: rollback. Nothing changes, and the webhook returns 500 or the reconciler retries on its next run.

- [ ] **12. Direct provider status check (guarantee that nothing sits pending for 24 hours)**
  - Starts: a reconciler job runs every 15 minutes. It selects refunds in `pending` where `last_provider_check_at` is null or more than 4 hours old. It also processes unmatched webhook events from step 10.
  - Action: call the provider's retrieve-refund endpoint by `provider_refund_id`, with the 10-second timeout and up to 3 retries on timeout or 5xx. Feed the result through step 11 and set `last_provider_check_at`.
  - Guarantee: a refund is checked at least every 4 hours, so no pending refund goes 24 hours without a direct check.
  - Escalation: a provider 404 or an unresolvable conflict moves the refund to `needs_review`. It is never auto-failed.
  - On failure: if the provider is unavailable, leave the refund `pending` and try again on the next run. Alert if a pending refund is older than 20 hours.

- [ ] **13. Customer email after success**
  - Starts: the email worker polls `email_outbox` for `pending` rows. Rows are created only in step 11, on the transition to `succeeded`.
  - Data: customer address from the payment's customer record, refund amount, and refund id. The internal reason and note are not included.
  - Idempotency: pass the outbox row id as the email provider's idempotency key, so retries do not send twice.
  - Stored: set `sent_at` on the outbox row and write `refund.customer_emailed` to the audit log.
  - On failure: retry with backoff. After a set number of attempts, mark the row failed and alert. The refund status is unchanged. No email is ever sent for `pending`, `failed` or `needs_review`.

- [ ] **14. Final outcome recorded**
  - Starts: the refund reaches `succeeded`, `failed` or `needs_review` (the last one ends only when a person resolves it).
  - Result:
    - The refund row has its final status and provider id.
    - The payment's order status is "Partially refunded", "Refunded", or unchanged (for a failure).
    - The audit log has the full history: request, each status change, and the email send.
  - Verification: an invariant check confirms that queued, pending, needs_review and succeeded amounts together never exceed captured. Concurrency tests run two simultaneous requests against one payment and expect one to be rejected.
  - This is the end of the flow.

---

## Open decisions for the team

- **429 and 408 responses:** both are 4xx, so the brief's rule would mark them failed without retrying. Retrying them is usually correct. Confirm whether they should be treated as retryable.
- **Provider API assumptions:** this plan assumes the create call returns the refund id, the retrieve-by-id endpoint exists, and the webhook signs the raw body with a timestamp. Confirm these against the provider's documentation.
- **`needs_review` owner:** who resolves these refunds, and what is the alert channel?
- **Note privacy:** the plan keeps the admin's free-text note off the provider. Confirm this is acceptable.
- **Email address source:** confirm the customer email comes from the payment's customer record and not from the card provider.