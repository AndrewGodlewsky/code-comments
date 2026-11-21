## Review of ml-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Replaced the 'Assumptions and open decisions' opening with a 2-3 sentence summary that says how the system works today (nightly table) and how the new flow runs start to finish.
- Added a Terms section (feature store, materialization job, registry, active pointer, shadow, candidate, fallback, warm), each in one line; the first version used these names without defining them.
- Merged the original 'Components' table with per-step state notes: one 'Where state lives' table, and trimmed repeated state lines from steps.
- Renumbered steps 1-17 to 1-16 by dropping the separate 'step 0' and moving the A/B gap out of the numbered flow into its own section; removed the 'Step 16 holds the gap' style pointers.
- Merged the old step 1 and 2 detail and the 'resolve_model' note, and folded 'Step 5 fallback' after inference so the flow reads in the order it happens.
- Moved all 'assumed' items into one short decisions list and said them once: model-failure fallback, latency split, salt, 7 days, rollback without approval, 10 s poll. Dropped the separate 'feature removal (assumed)' bullet because step 8 already states the rule.
- Added a failure summary table; removed the repeated 'if the registry is down' and 'previous version warm' explanations from several steps and said each once where it applies.
- Removed repeated explanations of the 6-hour rule, the shadow-skip rule and the rollback timing; each now appears in one place.
- Added to the shadow hand-off step that fallback responses are not sent to shadow (kept from the first version), and kept every number: 150 ms, 30 ms, 80 ms, 40 ms, 20 IDs, 6 h, 1 min, 10%, 7 days, 0.5%, 2 h and 4 h alerts, 5% drop rate, 45 s load test.
- Moved 'what to build first' to its own late section, separate from how the system runs, and moved open questions to the end, adding the automatic-rollback question that the first version only mentioned inline.
- Cut the 'Do not stop watching the dashboard' phrasing to 'Keep watching until every instance reports the new version' and cut the aside about bias from random drops to a one-line watch note.

### Holes
- None.
