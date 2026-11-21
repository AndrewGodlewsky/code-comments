## Review of ms-02 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered into summary, terms, shared rules, how it runs (after cutover), failure table, then rollout steps 1-10, then open questions, so running behaviour is separate from build/rollout.
- Merged the per-step repeated failure lists, the ownership table, and the final 'Summary of guarantees' table into one failure table; steps 5, 7, 9 now point to it instead of restating.
- Merged the repeated component descriptions (consumer, sender, relay, pager, publisher) into one 'How it runs' flow; steps 3 and 4 now say only what to build, deploy and verify.
- Added a Terms section defining monolith, old worker, service, broker, MailRelay, flag, route flag, relay, lease and the three types with volumes.
- Added a 'Rules that hold at every step' block holding retry policy, nothing lost/duplicated, rendering and ownership.
- Moved the three 'Assumptions to confirm' into Open questions and added the break-glass attempts gap there.
- Cut the separate Timeline-style prose repeats and the per-step 'Data moves' lines that said 'none' or 'unchanged'; kept the gate table.
- Kept every number and limit (5 attempts, 1/2/4/8, 24h key, 30s ack, 10s flags, 1s poll, 100/50 batches, 5s confirm timeout, 60s lease, 30-min alarm, 3/7 days, 60s p99, 30s alert, 36,000 samples, 15-minute drill watch, 15s rollback) and the residual risk note.
- No junior questions were provided, so I added no new content from answers.

### Holes
- None.
