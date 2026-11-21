## Review of pay-02 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-sentence summary and a short description of how refunds work today at the top; the first version had none.
- Added a Terms section defining captured, pending refund, idempotency key, request token, webhook, row lock, outbox, sweeper and shared transition.
- Merged the repeated fixed requirements (cents, cap, permission, 24h check, audit, order status, single email, final states) into one 'Rules that apply to every step' list; removed their repetition across steps.
- Deleted the 'Requirements covered' table because it repeated the steps; replaced it with a single failure table.
- Renumbered steps 1-13 (4a became step 5); replaced references like 'step 4a' with plain numbers and named the shared transition; moved the shared transition before the webhook handler's detail by keeping it as step 8 and order/email as steps 10-11.
- Merged the webhook handler's separate 'process' and 'processed_at' steps and the 'Concurrency control' sub-list into numbered reservation steps; merged the checks into fewer items.
- Dropped the data-section sentence about the order's display and the redundant 'Data moves: none further' lines; kept all numbers (10s timeout, 3 retries, 6h/15min/20h sweeper limits, 24h key window).
- Removed the Open-questions-free ending and added two honest open questions: email service idempotency support, and unspecified backoff timing and note length limit.
- Added a short note in the transition that a 4xx on a retry follows step 4's 4xx outcome, and that a final status in the provider's immediate reply goes through the shared transition.

### Holes
- None.
