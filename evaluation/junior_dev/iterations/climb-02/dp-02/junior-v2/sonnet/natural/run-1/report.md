## Review of dp-02 (junior-v2, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Definitions: added an 'Existing infrastructure' bullet (log, object storage, key-value store, warehouse, progress table), including how events_clean is partitioned (Q1, Q6).
- Dedup window definition: stated what happens to a copy after the key expires, and that the client contract rules it out (Q5).
- Step 3: spelled out client behaviour on 5xx/429/timeout and that the 7-day limit is the SDK buffer (Q2).
- Step 5: removed the false 'deterministic file name' claim; files are named from the offsets they hold, may overlap after a restart, and readers drop records with the same partition and offset; format left as an implementation choice (Q8).
- Step 6 and 11: archiver and live processor write watermarks to a progress table after each file or load (Q4).
- Step 7: stated that partition and offset come with each record from the log client (Q3).
- Step 13: rewritten so the replayed mark lives in the progress table and refused rows are dropped, counted and alerted, with no stall (Q7).
- Step 15: gate now reads the live watermark and archive watermark from step 11 and step 6.
- Step 17 and 25: replay drops overlapping archive records first, and the archiver restart test covers this.
- Open decisions: added a line for platform choices not in the brief.
- Step 11: replaced the deterministic batch identity with per-row log_partition/log_offset and a delete-then-reprocess on restart, so a crash between load and offset commit does not double-write.
- Definitions: added a single 'Watermark' definition with the idle-partition rule (now minus 1 hour when caught up) and a 5-minute skew margin for 'passed day D'.
- Step 6, 11 and 15: refer to the shared watermark definition instead of restating it.
- Step 13: rewrote to say exactly which events live still writes to D after midnight and what ends them, and to drop rows for any day that is 'started' or 'replayed'.
- Step 15: the gate marks D as 'started' when it passes, which closes the window between the archive read and the swap.
- Step 21 and 22: swap now relies on the 'started' mark; a failed replay leaves D 'started' and the rerun covers it.
- Step 25: added a crash between load and offset commit, and an idle-partition gate test.
- Definitions and Open decisions: warehouse delete-by-condition replaces the idempotent-load-by-job-id assumption.
- Merged old steps 23 (Monitor) and 24 (Reconcile) into one step 23; testing is now step 24. Lag and freshness alerts stay in steps 6 and 12 with no duplicate.
- Moved the 429/5xx/backoff handling and the partial-write note into step 3, and dropped the separate 'under load' and 'collector does not deduplicate' bullets as standalone items; the duplicate-removal pointer now correctly refers to step 7.
- Merged step 4's retention bullet into one line and removed the redundant 'Nothing downstream depends' wording.
- Merged step 6's lifecycle, watermark and alerting into one coherent step.
- Cut the 'Alternatively, resume and then replay' option from step 8 and kept only the archive rebuild.
- Shortened step 17's skew caveat and invariant check, and removed the repeated explanation of why later copies do not matter.
- Cut step 16's repeated rationale and step 19's statement about sharing a partition with live reads.
- Condensed the Definitions bullets and trimmed Open decisions, keeping the open items together at the end.
- Removed the bot-stage rationale repeated in step 10 and the Open decisions section where it said the same thing.

### Holes
- None.
