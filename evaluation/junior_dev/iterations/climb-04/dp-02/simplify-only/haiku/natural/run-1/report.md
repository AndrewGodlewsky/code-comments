## Review of dp-02 (simplify-only, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Removed the 'Decisions and open items' section. Its bot-traffic note moved into the bot-traffic step and the open questions. Its two assumptions moved into the open questions.
- Added a short summary at the top, stating the main flow, and a terms list with each term defined in one line.
- Stated the dedup rule once, in its own section. It was repeated in the live dedup step and the replay dedup step, and both now refer to that section by name.
- Rewrote all 21 steps in one shape: what starts it, what it does, what keeps its data, and what happens when it fails.
- Moved the failure details into one table. Removed the repeated failure text from the steps and merged the store-down and log-down rules into the table.
- Removed the requirement checklist table. It only pointed back to step numbers and repeated the steps.
- Merged the two archive lifecycle rules into one sentence and the close gate conditions into one list. Replaced step-number cross-references with step names.
- Added open questions where the original did not say what happens: enrichment failure, failures after the partition swap, and the length of the rollback period (the original said 'fixed period' with no length). Also added the unexplained-difference handling in the verify step. These are flagged as unknown, not decided.
- Kept the intent unchanged: W = 8 days, the late guard, the close gate, the bot-traffic no-op, read-only replay inputs, the swap order and the 5-minute freshness budget.

### Holes
- None.
