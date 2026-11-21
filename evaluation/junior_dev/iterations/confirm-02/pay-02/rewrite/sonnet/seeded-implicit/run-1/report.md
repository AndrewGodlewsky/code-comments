## Review of pay-02 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Replaced the 12-item checklist of one-line items with a summary, terms, numbered steps, a failure table and open questions, as the skill's layout requires.
- Added a short explanation of how refunds work today (provider dashboard, no refund table, existing payment table).
- Added a terms section defining captured payment, refund record, idempotency key, webhook, audit entry and the reason list.
- Added a rules section for facts that apply to every step: cents, the pending+succeeded cap, server-only provider calls, audit on every request and status change, and order status from succeeded refunds only.
- Merged 'Validate amount', 'Create refund record' and the concurrency requirement into one step that locks the payment row inside a transaction, so the cap holds for simultaneous admins.
- Merged 'Handle provider errors' into the provider call step, with the 10s timeout, 3 retries with the same key, and 4xx marks failed with the provider message shown.
- Merged 'Update refund status' into one shared function used by both webhooks and the reconciliation job, ignoring updates to refunds that are no longer pending so duplicate and out-of-order webhooks are harmless.
- Added order status and customer email as one step that runs only when a refund has just become succeeded, with an emailed mark set in the same transaction so the email is sent once per refund.
- Made the reconciliation job concrete, including the case where the provider call got no response, and the case where the 24-hour key window has passed.
- Added a failure table and an open questions section, with the job's schedule and threshold marked as suggestions.
- Moved audit logging from a final item into the steps that write it, so every request and status change is covered.

### Holes
- None.
