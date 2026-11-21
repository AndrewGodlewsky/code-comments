## Review of ms-02 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- No junior questions were shown, so the rewrite follows the skill's layout using my own reading of where a newcomer would stall.
- Opened with a summary of how sending works today (batch worker, 30 duplicates a week) and the new flow, plus the three rules that shape the plan.
- Moved the 'Design in brief' bullets into the summary and a terms section; added one-line definitions for broker, MailRelay, idempotency key, status, routing flag, dispatcher, old worker, lease and the three types.
- Split the runtime design (7 numbered steps: record, pick path, hand off, store, send, report back, reconcile) from the shipping plan (8 steps), the rollback and the timeline.
- Merged the repeated failure bullets from old steps 2 to 7 into per-step notes and one failure table; removed 'see Steps 3 and 4' cross-references.
- Merged step 3 and step 4 content (service sender, result publisher, pager, dispatcher, result consumer, reconciler) into the single run flow.
- Cut the Exit check and Failures sub-bullets of the shipping steps down to one line each; dropped the redundant stale-flag explanations (kept once in the failure table and once under rollback).
- Removed the redundant 'Data moved' and 'State' bullets per shipping step; the state table covers them.
- Merged the 'extra alerts' and latency-gate detail into steps 6 and 7 in fewer words; dropped the 'plenty of headroom' assertion, which is a claim, not a decision.
- Corrected the rollback heading from 'any time after step 5' to 'any time before step 8', since rollback stops being possible at step 8.
- Added the dispatcher-vs-old-worker arbitration into step 2 of the run flow, where a newcomer needs it.
- Added a rolled-back-type delay note in one line instead of repeating it in steps 6 and 7.
- Residual risks became the open questions section at the end; content unchanged.

### Holes
- None.
