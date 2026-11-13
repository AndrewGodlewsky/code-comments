## Review of dp-02 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary at the top, then a terms section that defines each name a newcomer would not know (log, partition, offset, consumer group, archive, KV store, SETNX, winner, enrichment, micro-batch, seal, staging table, atomic swap, watermark, run record). Everyday words such as batch and UTC day are defined in one line each.
- Added a 'Rules that apply everywhere' list for the cross-cutting facts (UTC day rule, dedup rule, 90-day retention, 5-minute SLA, closed-day rule, replay isolation), each stated once. Step text then keeps only the details of its own step.
- Separated how the system runs (live path, replay path, changes to an open day, failures) from build and rollout (verification), so verification sits in its own section at the end.
- Reworded the live steps so each stands alone: each names what starts it, what it does, what keeps its data and what happens when it fails. Removed cross-references such as step codes where possible.
- Merged the guardrail alerts into one list in step 12. The late-record alert is kept in step 11, where it applies, and the failure table repeats each alert once in plain words.
- Merged the log-retention explanation (14-day log too short for 90-day retention and the 8-day replay lookback) into the archive step, where it applies. Kept the reasons for the 8-day TTL and the 7-day retry bound at the steps that use them.
- Added a failure table covering each failure path from the brief and the steps.
- Kept every number, limit, setting and rule from the request and the first version: 100-event batch limit, 32 KB limit, 400/202/503 responses, 1 s to 5 min backoff, 7-day device buffer, 8-day TTL, 60 to 90 s micro-batches, 3/4/5-minute lag limits, 02:00 UTC close, 12-hour archive alert, the four seal conditions, the replay gate, the validation checks, the swap and rollback rules, and the verification tests. All open decisions are kept as open and none is chosen.
- Added two holes the first version did not list, both in the open questions: what the consumer does when SETNX errors, and what happens to a copy that arrives after its KV key expires.
- Kept the stated intent of the plan. No mechanism was added (no lock, lease, retry queue or takeover rule).

### Holes
- None.
