## Review of infra-01 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a Terms section defining colour, listener, target group, test listener, additive migration, ledger, advisory lock, image digest, deploy lock, watch, 5xx rate and state machine, so the steps can be read without outside knowledge.
- Replaced the numbered decisions with a short list of rules that apply across steps, and removed the cross-references by decision number. Each rule is stated once, where it applies.
- Merged the duplicated statements about the state table, the idle colour, the lock and the migration limits into single rules. Kept every number, limit and setting from the brief and the first version.
- Replaced the codes A1, R1 and R2 with named sections (Abort path, Manual rollback, Rollback after shutdown), so no step sends the reader elsewhere by code.
- Added the status `rolling_back`, which the steps use but the first status list omitted, and added `watching_started_at` and `watch_passed_at` to the deploy record, which the steps write but the first state table omitted. Step 13 now sets status `watching` and `watch_ends_at`, which the first version never set.
- Step 11 now says to abort if the deadline passes while an instance is out of the gate. The first version said only to return to step 9.
- Step 15 now releases the lock after setting `rolled_back`, matching the deploy state table and the manual rollback. The first version's automatic rollback step did not say when the lock is released.
- Step 15 now states that the shutdown timer does not run for the old colour once it is live again, instead of the first version's vaguer 'retention ends'. The intent is unchanged.
- Split the first version's long rollback step into an ordered list of four sub-actions, so the order of the conditional state change, the listener change and the lock release is explicit.
- Kept the 'Open questions and assumptions' section at the end and reworded it to refer to the health gate and the 'Launch' step by name, not by decision number.

### Holes
- None.
