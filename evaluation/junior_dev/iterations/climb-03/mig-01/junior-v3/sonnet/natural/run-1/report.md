## Review of mig-01 (junior-v3, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a two-sentence summary and a short Terms section (source of truth, sync, outbox, paused) at the top for newcomers.
- Stated that flags are cached per instance via app.flags and that the monitoring system scrapes app_flag_value; clarified the scrape interval in step 8.
- Explained why paused exists and what goes wrong if instances disagree on the source of truth.
- Defined inline sync (after commit, 250 ms, read current row, guarded upsert, success returned on failure).
- Defined the circuit breaker (per instance, in memory, 5 failures, 30 second skip, one probe).
- Said one repair worker polls both outboxes, covering the reverse direction.
- Added a Versions bullet saying the repository bumps version on every update.
- Added a per-mode delete() bullet covering users_erased and tombstones.
- Step 9: spelled out how the outbox drain is checked (COUNT is 0) and why setval is a one-time jump; noted Postgres sequence stays unused until the switch.
- Added an Open questions section for the unknown flag store and the initial breaker thresholds.
- Added an In-flight write term and made step 9 say the gauge covers the inline sync and that paused instances start no new inline sync (Q9).
- Stated who receives the 503 and that clients retry it automatically (Q10).
- Added a Who starts a step bullet and operator wording to steps 5, 6, 7 and 9 (Q11).
- Clarified in the Terms that the repair worker keeps running while paused, since it does the draining.
- Added the stuck-outbox-row response to step 9's failure handling and made step 8 explicit that the oldest outbox row must be under 5 seconds (Q12).
- Changed the read path: documented the stale-fallback case in dual_pg, and removed the MySQL fallback in pg_only, where MySQL is no longer updated, replacing it with one Postgres retry (Q13).
- Step 12 failure: replaced the false claim that the reverse outbox catches MySQL up with the real mechanism, a comparison run to zero mismatches feeding the Postgres outbox, and forbade step 11 rollback until it is clean.
- Step 6: said a mismatch is pushed into the outbox of the current source of truth, so the comparison repairs in either direction.
- Step 11 item 4: replaced the AUTO_INCREMENT check with an unconditional ALTER TABLE setting it past the largest id plus 1,000,000, mirroring step 9's setval.
- New ids decision: removed the sentence relying on MySQL moving its counter automatically and stated that rollback sets the counter explicitly.
- Replaced the long 'Design decisions' section with a shorter 'Rules every step relies on' placed after Terms, and ordered the document as summary, terms, rules, steps, open questions.
- Added Tombstone to the Terms and folded the outbox definition (schema, which side gets rows) into Terms instead of repeating it in the rules.
- Merged the repeated explanations of flag staleness, 30-second refresh and metric confirmation into one rule; merged the three separate setval/AUTO_INCREMENT id explanations into one New ids rule.
- Merged the 'Sync outbox', 'Sync copies state' and circuit breaker notes into one 'Writing and syncing' rule; merged the Postgres and MySQL version-rule and delete notes into two short rules.
- Removed cross-references such as 'step 9', 'step 6', 'step 11' and 'step 8' so each step stands alone; restated the needed conditions in place.
- Cut redundant lines (for example the repeated 'Rollback stays available', 'Healthy when' detail, the state lines on steps with no real state, and the duplicate rationale in the failure sections) while keeping every failure case.
- Renamed the 'Checklist' heading to 'Steps' and kept the Markdown checklist format required by the brief; no design change to the plan's intent.

### Holes
- None.
