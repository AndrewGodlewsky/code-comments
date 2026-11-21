# Plan: refunds from the admin page

## State the steps use

These are new, apart from `payments`, which already exists.

- **`payments`** (existing): `id`, `provider_charge_id`, `captured_amount_cents`, `status`, `order_id`.
- **`refunds`** (new), one row per refund attempt that an admin requests:
  - `id`: a UUID. It is also the **idempotency key** sent to the provider.
  - `payment_id`, `amount_cents` (integer, > 0), `reason` (enum: `duplicate`, `fraudulent`, `customer_request`, `other`), `note` (nullable, with a length limit).
  - `status`: `pending` | `succeeded` | `failed`. Only `pending` counts as open. `succeeded` and `failed` are terminal.
  - `submit_state`: `queued` | `submitting` | `accepted` | `unconfirmed` | `rejected`. This records where the provider call stands, separately from the refund's final result.
  - `provider_refund_id` (nullable, unique), `provider_message` (nullable), `attempt_count`.
  - `first_submitted_at`: the start of the provider's 24-hour idempotency window.
  - `lease_until`: the time until which a worker's claim on the row is valid.
  - `next_check_at`: when the reconciler next looks at this row.
  - `requested_by` (admin id), `client_request_id` (unique together with `payment_id`), `created_at`, `updated_at`.
- **`webhook_events`** (new): `provider_event_id` (unique), `type`, `provider_refund_id`, `our_refund_id` (from metadata), `payload`, `received_at`, `processed_at`, `match_state` (`matched` | `unmatched` | `conflict`).
- **`email_outbox`** (new): `refund_id` (unique, which is what makes "only once" hold), `status` (`queued` | `sent` | `failed`), `attempts`, `sent_at`.
- **`audit_log`** (new, append-only): `actor` (an admin id, or `system:worker` / `system:webhook` / `system:reconciler`), `action`, `refund_id`, `payment_id`, `old_status`, `new_status`, `details` (JSON), `created_at`. Every audit entry is written **in the same database transaction** as the change it describes, so no change can exist without its audit entry.

All status changes go through one function, `transition(refund_id, new_status, actor, details)`. It runs `UPDATE refunds SET status = :new WHERE id = :id AND status = 'pending'`. Steps 7, 8 and 9 all use it. Because of the `AND status = 'pending'` guard, a terminal state can never be overwritten.

## Steps

- [ ] **1. Admin opens the payment in the admin page**
  - **Starts it:** an admin navigates to `/admin/payments/:id`.
  - **Data:** the browser sends the session cookie to our server. The server returns the payment (captured amount, status), its existing refunds with their statuses, the **remaining refundable amount** (`captured_amount_cents − sum(amount_cents of pending and succeeded refunds)`) and a fresh `client_request_id` for the form.
  - **State:** read-only. Nothing is written.
  - **On failure:** if the admin lacks refund permission, the page is shown without the refund form. The server enforces the same rule again in step 3. If the payment is not `captured`, the form is hidden and the page explains why. The remaining amount shown here is only a guide. Step 3 does the real check.

- [ ] **2. Admin submits the refund form**
  - **Starts it:** the admin enters an amount, picks a reason, optionally types a note, and clicks Refund. The button disables itself after the click.
  - **Data:** `POST /admin/payments/:id/refunds` from the browser to **our server only**, with `{amount_cents, reason, note, client_request_id}`. The browser never contacts the provider.
  - **State:** none yet.
  - **On failure:** if the request fails on the network, the admin can resubmit. A resubmission carries the same `client_request_id`, so step 3 will not create a second refund.

- [ ] **3. Server validates and reserves the amount (one database transaction)**
  - **Starts it:** the POST from step 2.
  - **Data:** the server checks, in this order:
    1. The session belongs to an admin with refund permission. If not: `403`.
    2. `amount_cents` is an integer greater than 0, `reason` is one of the four values, and `note` is within the length limit. If not: `422`.
    3. A refund with the same `(payment_id, client_request_id)` already exists. If so, the server returns that refund and does nothing else.
  - **State:** in one transaction, in this order:
    1. `SELECT … FROM payments WHERE id = :id FOR UPDATE`. This locks the payment row, so two admins refunding the same payment are handled one after the other.
    2. Check `payments.status = 'captured'`.
    3. With the lock held, compute `sum(amount_cents)` of that payment's refunds where `status IN ('pending', 'succeeded')`. The isolation level is READ COMMITTED, so this query sees any refund another transaction committed while this one waited for the lock.
    4. Check `amount_cents <= captured_amount_cents − sum`.
    5. Insert the `refunds` row with `status = pending`, `submit_state = queued` and `next_check_at = now + 1h`.
    6. Insert the audit entry `refund.requested`, recording the admin, amount, reason and note.
    7. Commit.
  - **On failure:** if the payment is not captured, or the amount exceeds what remains, the server returns `409` with the current remaining amount, and the admin sees "Only $X.XX can still be refunded." Nothing is written. If the transaction itself fails, it rolls back, nothing is written, and the admin sees a generic error and can retry. The new refund row counts against the total from this moment, before the provider is ever called. That is why the cap holds even while the call is in flight.
  - The server answers `202` with the refund id. The admin page now shows the refund as "Pending – sending to provider" and polls `GET /admin/refunds/:id` every few seconds (see step 6).

- [ ] **4. Worker sends the create-refund call to the provider**
  - **Starts it:** a background worker picks up `refunds` rows with `submit_state = queued`. It also picks up rows with `submit_state = submitting` whose `lease_until` has passed, which means an earlier worker crashed mid-call. The call runs in a worker, not in the HTTP request, because the worst case (4 attempts × 10 s plus backoff) is too long to keep a browser request open.
  - **Data:** the worker claims the row by setting `submit_state = submitting` and `lease_until = now + 2 min`, and sets `first_submitted_at` if it is still empty. It then sends `create_refund(charge = provider_charge_id, amount = amount_cents, reason, metadata = {our_refund_id})` with the header `Idempotency-Key: refunds.id` and a **10-second timeout**.
  - **State:** `attempt_count` is incremented on the refund row before each attempt.
  - **On failure:**
    - **Timeout or 5xx:** retry with the **same key**, up to 3 retries (4 attempts in total), with backoff of about 1 s, 2 s and 4 s plus jitter. The same key guarantees that a retry returns the original refund instead of creating a second one.
    - **4xx:** stop immediately and go to step 5b. No retry.
    - **Worker crashes mid-call:** the lease expires and another worker, or the reconciler (step 9), resends with the same key. This is safe while it happens within 24 hours of `first_submitted_at`.

- [ ] **5. Record the provider's immediate answer**
  - **Starts it:** the last attempt in step 4 has returned or given up.
  - **a. 2xx (accepted):** in one transaction, store `provider_refund_id`, set `submit_state = accepted` and keep `status = pending`, because 2xx only means "accepted". Set `next_check_at = now + 1h` and write the audit entry `refund.submitted`. If a webhook has already been stored for this refund as unmatched (step 7), apply it now.
  - **b. 4xx (rejected):** in one transaction, set `submit_state = rejected` and `provider_message` to the provider's error text, then call `transition(→ failed, actor = system:worker)`, which writes the audit entry `refund.failed`. The amount is released, because failed refunds do not count toward the total.
  - **c. All retries exhausted on timeouts or 5xx:** we do not know whether the provider created the refund. Set `submit_state = unconfirmed` and **keep `status = pending`**, so the amount stays reserved. Set `next_check_at = now + 15 min` and write the audit entry `refund.submit_unconfirmed`. Step 9 resolves it.
  - **On failure:** if the database write fails after the provider answered, the row stays in `submitting`. Its lease expires, and the resend (same key) gets back the same provider refund, so writing the answer is safe to repeat.

- [ ] **6. Admin sees the immediate result**
  - **Starts it:** the admin page polls `GET /admin/refunds/:id`. The permission check is enforced again here.
  - **Data:** server → browser: `status`, `submit_state` and `provider_message`.
  - **State:** read-only.
  - **What the admin sees:** "Pending – accepted by provider, waiting for final result" (5a). For 5b, "Failed" with the **provider's message** shown word for word. For 5c, "Pending – provider did not confirm, we are checking automatically". If the admin closes the page, nothing is lost: the refund's state is in our database and shows on the payment page from step 1.

- [ ] **7. Receive a refund webhook (`refund.succeeded` / `refund.failed`)**
  - **Starts it:** the provider sends a POST to `/webhooks/provider`. This can happen minutes or days later, more than once, and out of order.
  - **Data:** the raw request body plus the signature header.
  - **State:**
    1. Verify the signature over the **raw** body with the webhook secret. If it is invalid, return `400`, write nothing, and log it.
    2. Insert into `webhook_events` keyed on `provider_event_id`. If that id is already there (a duplicate delivery), return `200` and stop.
    3. Find the refund by `provider_refund_id`. If that fails, try `metadata.our_refund_id`. The second lookup is needed when the webhook arrives before step 5 has stored the provider id (for example, after 5c).
    4. If neither lookup finds a refund, mark the event `unmatched`, return `200`, and leave it for step 5a or step 9 to apply.
  - **On failure:** if the database is unavailable, return `5xx` so that the provider redelivers. Return `200` only after the event has been stored.

- [ ] **8. Apply the webhook's result to the refund (one database transaction)**
  - **Starts it:** a matched event from step 7.
  - **Data:** the event type, plus the amount and provider refund id from the event.
  - **State:**
    - Check that the event's amount and refund id match our row. If they do not, mark the event `conflict` and alert support. The refund is not changed.
    - Call `transition(→ succeeded | failed, actor = system:webhook, details = {provider_event_id})`, which writes the status-change audit entry. If the result is `succeeded`, insert an `email_outbox` row for this `refund_id` in the same transaction (step 10).
    - Mark the event `processed_at = now`.
  - **On failure:**
    - **Duplicate or out-of-order delivery:** if the refund is already terminal with the **same** status, the guarded update changes 0 rows. Nothing happens and the event is marked processed.
    - **Contradicting a terminal state:** if the event contradicts a terminal status we already hold (for example, `failed` after `succeeded`), the status is **not** changed. Instead, mark the event `conflict`, write an audit entry `refund.webhook_conflict`, and alert support to check by hand.
    - **Transaction error:** the transaction rolls back and the endpoint returns `5xx`, so the provider redelivers.

- [ ] **9. Reconciler checks pending refunds with the provider directly**
  - **Starts it:** a scheduled job every 15 minutes picks `refunds` rows with `status = pending AND next_check_at <= now`. Webhooks alone are not relied on.
  - **Data and state, by case:**
    - **`provider_refund_id` is known:** fetch the refund from the provider, using the same 10-second timeout and retry rules as step 4.
      - If the provider says succeeded or failed, call `transition(…, actor = system:reconciler)`. This has the same effects as step 8, including the email outbox row.
      - If it is still pending, write the audit entry `refund.status_checked` and set `next_check_at` to `now` plus an interval that grows from 1 h to a maximum of 6 h.
      - Under this schedule, every pending refund is checked with the provider well within 24 hours, and at least every 6 hours after that.
    - **`submit_state = queued` or `unconfirmed`, or a `submitting` row whose lease has expired:**
      - If `first_submitted_at` is empty (the refund was never sent), or the first send was less than about 22 hours ago (a margin inside the 24-hour idempotency window), resend create-refund with the **same key** and handle the answer as in step 5.
      - If the window has run out, the key can no longer be reused safely. The refund stays `pending` (the amount stays reserved), and the reconciler looks for it among the provider's refunds for that charge, matching on `metadata.our_refund_id`.
    - **Unmatched webhook events:** retry matching them (step 7) and apply any that now match (step 8).
  - **On failure:** if the provider is unavailable, leave the row unchanged and set `next_check_at = now + 15 min`, so it is retried on the next run. Alert support in two cases: a refund has been `pending` for more than 3 days, or an `unconfirmed` refund cannot be found at the provider after its key window has run out. Support resolves these with an audited manual action. They are never left to sit silently.

- [ ] **10. Email the customer once, after success**
  - **Starts it:** an `email_outbox` row with `status = queued`. This row is created only by a transition to `succeeded` (step 8 or 9), and only once, because `refund_id` is unique in `email_outbox`.
  - **Data:** an email worker sends the customer's email address, the refund amount and the order reference to the email service. If the email service accepts an idempotency key, the worker sends `refund_id` as that key.
  - **State:** after sending, set `email_outbox.status = sent` and `sent_at`, and write the audit entry `refund.customer_emailed`.
  - **On failure:** retry with backoff up to 5 times. After that, set `failed` and alert support. The refund itself is not affected. If the worker crashes between sending and marking `sent`, the email can go out twice, unless the email service accepts our `refund_id` as an idempotency key.

- [ ] **11. Order status reflects succeeded refunds**
  - **Starts it:** any read of the order, on the admin page or elsewhere.
  - **Data:** `succeeded_total = sum(amount_cents of refunds where status = succeeded)` for the order's payment.
  - **State:** computed when the order is read; nothing extra is stored.
    - If `succeeded_total = 0`, there is no refund label.
    - If `0 < succeeded_total < captured_amount_cents`, the order shows "Partially refunded".
    - If `succeeded_total = captured_amount_cents`, it shows "Refunded".
    - Pending and failed refunds never change the label.
  - **On failure:** none specific to this step. The label is recomputed on every read, so it cannot drift from the refunds table.

- [ ] **12. Final outcome is recorded**
  - **Starts it:** the refund reaches `succeeded` or `failed` (step 5b, 8 or 9).
  - **State:** the `refunds` row is terminal and can no longer change, because of the `status = 'pending'` guard. The audit log holds the full history: who requested the refund, what was sent, each status check, and the final status with its source (worker, webhook or reconciler). The order label (step 11) and, for successes, the email (step 10) follow from it. Step 9 no longer selects the row.
  - **On failure:** a later contradicting webhook does not change the status. It is handled as a conflict in step 8.

## Assumptions to confirm with the provider's documentation

- Create-refund accepts `metadata`, and webhooks and fetches return it. Steps 7 and 9 depend on this to match a refund whose create call timed out.
- There is an API to fetch a refund by id, and to list the refunds on a charge. Step 9 depends on this.
- How the provider answers a retry that arrives while the original request with the same key is still in progress, for example with a `409`. The brief says every 4xx means rejected. If the provider uses `409` for this case, treating it as rejected would wrongly fail a refund that may have been created, so `409` may need to be retried instead.
