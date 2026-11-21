## Review of search-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short terms section (WAL, slot, LSN, version, active index, consumer group) so a reader new to the stack can follow.
- Reordered the live path into numbered steps: poll, dedupe per id, translate, version, write, commit offsets.
- Moved the explicit batch trigger (500 events or 500 ms) into the text so it matches the diagram.
- Corrected the conflict wording: with an at-least rule, only events older than L0 conflict (not at or below), since an equal version is applied again harmlessly.
- Rewrote rebuild step 3 as a lettered ordered list and noted that overlap between snapshot and topic is safe.
- Clarified step 7 that indexer-rebuild feeds the new index and indexer-live the old one, and removed duplication.
- Reworded failure-handling and rollback text to be shorter and less ambiguous; explained what the 'delete resurrection' risk is.
- Fixed the diagram: split the slot-drop failure note so it no longer claims the slot drop triggers the 20 GB alert, tightened labels, and added a legend line under Flowchart.
- Split the state-topic edges so R3 stores phase, E, L0 and R5 stores the last loaded id, matching the prose.
- Added a pointer that steps R0 to R14 in the diagram correspond to the numbered rebuild steps.
- Fixed the mismatch between the rebuild list (numbered 1-9) and the diagram (R0-R14): the rebuild steps are now labelled R0-R14 in the same order as the diagram nodes, and diagram node text carries the same labels.
- Expanded the terms section for readers new to the stack: added CDC/Debezium, topic/partition/offset, repeatable-read snapshot, compacted topic and DLQ, and explained what committing offsets means.
- Defined the hex-to-integer version formula more plainly (hi and lo are the parts either side of the slash) and spelled out op values c/u/d.
- Stated the freshness budget total (3.5 s, 1.5 s margin).
- Clarified the roles of indexer-live and indexer-rebuild after the switch: after 48 hours the rebuild group becomes the live sync, and the next rebuild needs a fresh group name.
- Noted in the first-migration item that the old index is fed by the cron, not indexer-live.
- Added a pointer from the failure table to the loader-specific failures in R6/R7, and moved the slot-dropped-during-rebuild case into the labelled list.
- Moved the rollback and cleanup steps into separate labelled items (R13, R14) and removed the duplicated cron-retention sentence wording.
- Added a short two-bullet overview (live path, rebuild) at the top so the reader has the whole shape before the details.
- Expanded the alias definition into 'Alias and active index' so the alias/concrete-index distinction is explained once.
- Live step 4 now says each indexer group writes to one fixed concrete index (the active index in steady state), resolving the apparent contradiction with R12 where indexer-live feeds the old index.
- Moved 'keep latest event per id' to a per-batch step in the flowchart node L2 so its order matches the prose.
- Added a short intro to the Rebuild section explaining E and L0 before they are used.
- R12 and its flowchart node now say each group feeds its own index; R14 names indexer-live explicitly as the group being stopped.
- Clarified the slot-dropped-during-rebuild case: E is no longer valid, so abandon the partial index and restart from R1 (prose and flowchart).
- Noted that the 'under 5 s behind' gate depends on the same missing timestamp as the freshness target.
- Removed redundant wording in the R3 step list (E described once, in the intro).

### Holes
- None.
