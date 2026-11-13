## Review of dp-02 (junior-v4, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Step 11: named the seal job as a scheduled job (02:00 UTC, retry every 5 min), and said it waits and alerts at 04:00 UTC if the archiver is behind.
- Step 9: said the live job checks whether sealed/dt=D exists (cached up to 1 minute), defined the quarantine location as quarantine/dt=D/, and said that nothing moves quarantined records and a replay picks them up.
- Step 5: explained that a chunk of offsets is split into one file per received_at day, that offset ranges of different days may interleave, and that the checkpoint is committed after all files of the chunk.
- Step 6 and step 9: said that dropped duplicates are counted and their offsets are committed with the micro-batch. Also added the one-consumer-per-partition ordering requirement.
- Step 8: gave the hook's position (after dedup and enrich, before the warehouse write) and said it passes everything through until Product decides.
- Step 2: added the 202 body with the rejected list and the 4xx body for whole-batch rejection.
- Step 13 and A3: said that the live claim order and replay's earlier-log-order rule agree because all copies of an event share one partition and offset order.
- Open items: added the dependency on consumer-group fencing.
- Step 9: added warehouse write failure handling (retry the same micro-batch, no offset commit, lag builds, freshness alert fires).
- Step 5: added archiver crash recovery after partial files, and the stale-marker check before writing a file for a sealed day.
- Step 11: defined stale/dt=D detection and the `seal --day D --force` re-seal procedure.
- Step 12: defined the replay lock as an object replay-lock/dt=D, its release on run end, and manual `--release` after a crash. Preflight now checks stale/dt=D.
- Step 15: stated the state after a failed validation and the operator's next options, including the recorded override.
- Step 16: stage dropped only after a successful publish, and the override is logged. This replaces the earlier wording that a failed run drops the stage.
- Added assumption A5 (object storage create-if-absent) and the matching open item.
- Step 19: added an archiver crash test.
- Reordered into the newcomer layout: summary, terms, diagram, then numbered steps, a failure table, guarantees, and open questions at the end
- Added a short terms section (event, received_at, dt, duplicate, envelope, closed day, seal, stage) and removed the separate data-contract step by moving it into terms and steps
- Merged old steps 2-4 (validate, stamp/append, failure) into two collector steps, and old steps 5-6 and enrichment kept as separate stand-alone steps
- Folded the latency budget and monitoring into one monitoring step and merged old retention, isolation and tests sections into shorter sections
- Gave every step the same four parts: starts, does, data, goes wrong
- Separated running the system (live and replay) from building and launching (build order, tests)
- Replaced codes A1-A5 and step cross-references with plain descriptions; moved the assumptions into the open-questions table at the end
- Cut the Open decision section and duplicate bot-traffic text into step 6 and the table
- Cut the deduplicated failure explanations across steps into one failure table; shortened validation, seal and archiver prose
- Added the consumer-group fencing assumption to the table and kept the A3 partition-count assumption inline

### Holes
- None.
