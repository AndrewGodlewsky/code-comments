## Review of ms-01 (rewrite-v5, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- No junior questions or answers were supplied, so the rewrite is driven by the skill's clarity rules and the brief. No question-driven fixes were made.
- Added a plain summary paragraph at the top saying what checkout is now, how the flow runs from start to finish, and why it is ordered as hold, then charge, then claim.
- Added a Terms section defining service, snapshot, hold, claim, release, sweeper, provider, charge, refund, webhook, idempotency key, event, outbox, processed event ids and STUCK in one line each.
- Replaced the flat diagram-first layout with a numbered step list placed after the diagram. Each step says what starts it, what it does, which service keeps its data, and what happens when it goes wrong.
- Merged the duplicate idempotency rules (reservation, charge and claim keys) into one rule in the summary.
- Added a failure table covering short stock, declined payment, late success after the hold expired, duplicate webhook, missing webhook, retried charge, refund not accepted, and checkout failing for any reason.
- Replaced the undefined 'N tries' in the refund retry node with 'a set number of tries' and moved the missing number to the open questions.
- Added open questions for gaps the brief does not cover: refund retry count and backoff, provider unreachable on charge, no reply to the claim call, and cart clear failure after confirmation.
- Kept the Mermaid flowchart with its branches and services. Only labels were made plainer, and the step notes refer to steps by number instead of node codes.
- Cut the internal node codes from the prose, the separate 'Write your answers' style phrasing, and repeated statements of the same refund rule. Moved the 'never ship partial orders' rule into the step notes where it applies.
- Left the diagram form in place: summary and terms before it, notes after it. Kept the document within about one and a half times its original length.

### Holes
- None.
