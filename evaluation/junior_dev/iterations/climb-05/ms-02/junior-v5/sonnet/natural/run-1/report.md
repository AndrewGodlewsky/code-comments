## Review of ms-02 (junior-v5, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a short paragraph on how the old worker runs today (5 s poll, batch of 50, SKIP LOCKED, per-batch commit, where attempts and next_attempt_at are set) because Q1 showed the plan assumed it.
- Defined tx and enqueue_notification's transactional behaviour in one sentence in Design in brief (Q2).
- Specified the consumer behaviour for an existing but non-terminal row: no-op, then ack (Q3).
- Added the missing outbox publisher behaviour (1 s poll, published_at marker, republish on crash) and a published_at column on the outbox table (Q4).
- Made the pager an explicit component with a 10 s loop over failed, unpaged rows, and listed it in Roles of the pieces (Q5).
- Stated the outcome event contents and the behaviour for non-handed_off rows in the outcome consumer (Q6).
- Clarified that the reconciler republish of a still-retrying row is a no-op in the service (Q7).
- Defined flags.get and who flips flags, and added an Open questions entry because flag storage and tooling are not described in the existing files (Q8).
- Added a 'The broker' paragraph defining the existing broker, storage confirmation and the two topics (Q10).
- Defined a 'due' service row and the lease in Service row states, and gave the sender a 1 s poll (Q9).
- Fixed a gap: the sender now clears lease_until on retry and on success, and says how a retry-wait differs from a crashed send (Q12).
- Said that the service ignores attempts and next_attempt_at from a republished message for an existing row (Q14).
- Added a 10 s limit on the dispatcher's publish phase so a slow broker cannot hold row locks, and noted the outcome consumer is not blocked (Q13).
- Spelled out what happens to a dead-lettered message and added the dead-letter queue owner to Open questions (Q11).
- Added service-side alerts for DB down, outbox backlog, stuck sender and a non-empty dead-letter queue (Q15).
- Restructured into the required order: summary (with how the system works today), terms, how it runs (numbered lifecycle steps), failure table, rollout steps, open questions.
- Separated runtime behaviour from rollout: the eight runtime steps (record, dispatch, receive, send, page, publish outcome, apply outcome, reconcile) are now apart from the ten shipping steps.
- Added a Terms section covering broker, storage confirmation, idempotency_key, route flag, statuses, due, lease and outbox.
- Merged per-step 'same as step 6' failure and rollback text into one shared rollback paragraph and one failure table.
- Merged the repeated 'why nothing is lost or duplicated' bullets into the summary and the honest-limit note.
- Cut the per-step Starts/Data/State/Failures bullet scaffolding in rollout steps in favour of compact paragraphs, and trimmed the exact schema detail for the migration.
- Folded the old worker description (poll, claim, attempts/next_attempt_at) into the summary; stated that tx is the caller's transaction.
- Kept all decisions (1 s polls, 10 s publish limit, 10 s pager, alert thresholds) and noted thresholds are our choice, not requirements.
- No behavioural changes to the plan.

### Holes
- Q8: What is `flags.get` and where are flag values stored and changed? Who flips a flag during rollback, and how? (author: flags.get(name) is the monolith's runtime flag lookup, and a change reaches every instance within 10 s (from notifications-overview.md). The existing files do not say where flag values are stored, who may change them, or how. I assume the Platform team flips them with the existing flag tooling, but I cannot confirm it. Added to Open questions.)
- Q11: If a handoff goes to the dead-letter queue, its monolith row stays handed_off. What happens to that row afterwards? Does the reconciler keep republishing it into the same dead end, and who clears the queue? (author: The files do not say who owns or clears a dead-letter queue. The monolith row stays handed_off; the reconciler republishes it after 30 min, which is a fresh try, and the 1 h alert fires if it stays stuck. I assume on-call clears the queue by hand, which I cannot confirm. Added to Failures and Open questions.)
