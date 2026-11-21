## Review of ml-01 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Merged the 9-line list into a summary, a terms list, 9 stand-alone steps with trigger, data, state and failure handling, a failure table, open questions and a build order.
- Added every fixed requirement from the brief that the first version dropped: 150 ms p99, 30 ms lookup, 6-hour staleness, 20 items, 10% by user ID, 7 days, 0.5%, 80 ms, ML lead approval, 1-minute rollback; placed them in a short rules list and at the steps they apply to.
- Added terms: online feature store, materialization job, registry, alias, shadow, fallback, required features, prediction log.
- Added today's nightly-table behaviour in the summary.
- Added decisions: registry polling every 15 s, inference timeout 100 ms, fallback on model error, background load then swap, rollback needs no approval, dropped shadow copies when queue is full, shadow hash by user ID modulo 100.
- Merged old steps 8 and 9 content with a clear switch/rollback mechanism and the previous alias; moved old step 4 feature check to apply at load, at shadow start and at switch.
- Merged shadow queue, workers and prediction log into one shadow step; split promotion criteria from the switch and kept the A/B gap as a neutral slot between them without choosing.
- Added a failure table and open questions (A/B test, tuning values, where approval is recorded); separated build order from runtime.

### Holes
- None.
