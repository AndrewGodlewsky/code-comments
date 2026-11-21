## Review of pay-02 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the thin one-line checklist into 12 ordered steps. Each step now says what starts it, what data moves, where state is stored and what happens on failure, as the brief's format asks.
- Added a short Terms and records section that defines captured amount, refund statuses, open total and the new refunds and refund_audit tables, so a reader new to the project can follow the steps.
- Spelled out how the cap holds under concurrent refunds: a row lock on the payment, summing pending and succeeded refunds, and a pending row inserted before the provider call, with the lock released before the network call.
- Described the provider call in detail: the idempotency key is created once and reused, the 10-second timeout, up to 3 retries on a timeout or 5xx, and no retry on a 4xx, which marks the refund failed and shows the provider's message.
- Added the case where retries run out, so the outcome is unknown. The refund stays pending, and the reconciler resolves it by repeating the call with the same key within 24 hours.
- Described webhook handling: signature check on the raw body, duplicate events dropped by event id, out-of-order events handled by a conditional update that only changes a pending refund, and a conflict audit and alert for contradictory results.
- Added the reconciliation job with a schedule and a recheck interval, and a stated guarantee that no refund stays pending for 24 hours unchecked.
- Added order status calculation from succeeded refunds only, recomputed rather than incremented. Added once-only customer email, queued in the same transaction as the success change.
- Folded audit logging into each step, with an audit entry per request and per status change, and listed the entry types in the final step. Replaced the old standalone 'Audit logging' item.
- Added a short list of assumptions to confirm, such as provider metadata and lookup support, the reconciler schedule and the admin's wait time.
- Added a short 'How it works in brief' overview so a reader new to the project sees the whole flow first.
- Defined idempotency key, and added the webhook_events table to the terms list (it was used but never defined).
- Fixed a correctness bug: the webhook event id is now recorded in the same transaction as the status update (step 8), so a failed update cannot leave an event marked as seen and then ignored on redelivery. Step 7 now points to step 8 for this.
- Corrected the worst-case wait from about 40 to about 47 seconds (4 attempts x 10s plus 1+2+4s pauses) in steps 5 and the assumptions.
- Step 5 now explicitly sends our refund id as metadata, which step 7 relied on.
- Removed the assumption that the provider can look up by idempotency key, since step 9 does not need it.
- Clarified the retry count as 4 attempts in all, and clarified who writes the audit entry in step 9.
- Simplified step 7 (state stored now says nothing, step 8 does the writing), removed redundant 'total is 0' case in step 10, and tightened wording and the clumsy payments/order sentence.
- Moved 'No email for failed refunds' next to the queuing rule in step 11.
- Defined 'webhook' in plain words in the overview, and said the webhook and reconciler share one routine.
- Step 7: added that the verified result is passed to step 8, so the handoff is explicit.
- Step 8: split the single dense paragraph into a numbered sequence (insert event id, conditional update, handle 0 rows).
- Step 9: broke the two lookup cases and the handoff into sub-bullets.
- Step 11: reworded 'the job is queued' to 'a job is queued' for clarity.
- Minor wording tightening in the overview and the idempotency key definition.

### Holes
- None.
