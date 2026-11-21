## Review of pay-02 (junior, author sonnet, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote each step as a checklist item with trigger, data, stored state and failure handling, since the questions showed the one-line steps left these out.
- Added the refund record fields and starting status, with the UUID id used as idempotency key.
- Added a payment-row lock in one transaction for amount validation and record creation, so simultaneous refunds cannot exceed the captured amount.
- Defined what is left on the payment as captured minus pending and succeeded refunds, failed excluded.
- Stated that POST /refunds returns after the provider call, and that the admin sees the final result on page reload.
- Specified webhook handling: raw-body signature check, matching by provider_refund_id, safe duplicates and out-of-order via update only when pending.
- Defined order status and email rules from succeeded refunds only, with email_sent_at as the once-only guard.
- Specified the reconciliation job schedule and behaviour, including repeat of the create call with the same key and the 24-hour key expiry.
- Added the audit log table and an Open questions section for provider lookup/metadata support and the job timings.
- Merged old steps 3 and 4 (validate amount, create record) into one step 3, since they share one transaction; moved the table fields and audit_log columns there.
- Merged old step 6 (provider errors) into step 4 as per-outcome bullets, and folded the endpoint's return behaviour there, so each outcome appears once.
- Merged old steps 9 and 10 (order status, email) into step 7 since both follow the status update.
- Moved the old audit logging step 12 into a rules section (audit every request and status change; system actor), and the old `status` field note into the terms.
- Added a Terms section (captured, provider, idempotency key, webhook, accepted, status values, what is left) from the junior's questions about meaning.
- Added a short summary of how refunds work today and how the new flow goes, and a single failure table; removed the repeated per-step failure restatements where the table covers them.
- Added a 'Rules that hold in every step' section keeping every brief requirement (cents, cap, concurrency, reasons, server-only, 24h check, email once, order status, audit).
- Renumbered steps (reconciliation is now 8) and updated cross-references; removed codes pointing elsewhere by naming the step content.
- Cut detail nothing asked for: the 'form only reads data' elaboration shortened, the 'email never sent for pending or failed' repeat, and the long explanation of 15-minute choice (kept as an open question).
- Added the signature algorithm as an open question since a junior asked how verification works and the plan does not decide it.

### Holes
- None.
