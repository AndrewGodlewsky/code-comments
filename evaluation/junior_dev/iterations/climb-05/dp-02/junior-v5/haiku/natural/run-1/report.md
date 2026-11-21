## Review of dp-02 (junior-v5, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Definitions: added 'Log offset' and 'Enrichment version'. Reworded 'Closed day' to use log offsets instead of a received_at watermark, because the watermark could not prove completeness (Q1, Q2).
- Step 3: added the 30-second append timeout, and explained that a lost 202 makes the retry the main source of duplicates (Q6).
- Step 5: added that a down or slow key-value store stops the partition and does not skip the record (Q4).
- Step 5c: said that the release process sets the enrichment version and consumers run the version they were deployed with (Q5).
- Step 5d: the ledger is now one idempotent object per received day, partition and offset range, in object storage, written before the warehouse commit (Q3).
- Step 6: consumers commit offsets only after the warehouse batch commits, and a record for a closed day is skipped and alarmed (Q1, Q7).
- Step 8: replaced the received_at watermark with a fence, an end-offset snapshot and an offset wait. Added the clock-skew alarm threshold of one minute, which is my choice (Q1, Q2).
- R1: stated that replay is manual only (Q8).
- R7: added the ABORTED outcome, that closed days are not reopened, and how a late record is handled (Q7).
- Open item 8 added: the replay trigger interface is undecided (Q8).
- Open item 5: noted that claim order approximates arrival order (Q6).
- Definitions: added the day status row, and rewrote Closed day so the close job writes the mark after step 8 passes. The old wording (marked closed at 02:00) contradicted step 8. Answers Q10.
- Step 6: the batch transaction reads day_status for each partition day in the batch and skips closed days, so the check and the write are atomic and not based on a cached mark. Answers Q10.
- Step 8 Fence: the job polls every collector's status call for its in-flight count for D. Silence, a down collector or a restart blocks or restarts the poll, and a pre-crash append after the fence is routed to the late-record path. Answers Q9.
- Step 8: added the final action, writing D's status row as closed with the snapshot offsets, and what step 6 does after that.
- R7: replaced the 'no live write to D is pending' check with a status re-check in the same transaction as the swap, ordered against live writes by the warehouse. Answers Q11.
- Open item 6: added that a transaction reading day_status and writing a partition must be serialized against a partition replace.
- Open item 9 added: the brief says a day closes at 02:00 UTC on D+1, but the wait step can finish later. This is a real conflict with the brief, so it is recorded as an open question and not decided.
- Checks before launch: added a check that a down collector blocks the close.
- Definitions, Received day: stated that the day runs from 00:00:00 to 23:59:59.999 UTC and gave the 00:30 UTC on D+1 example.
- Definitions, Winning copy: said claims follow processing order and that a dropped copy can have an earlier received_at than the winner.
- Definitions, Closed day: removed the reference to open item 9 and kept the rule that the row is written only after the three parts of step 8 pass.
- Step 5b: added that a dropped copy can have an earlier received_at than the winner, and that the winner's own received_at still sets the partition.
- Step 8 intro: explained that the two hours after midnight let in-flight batches finish and records be processed.
- Step 8 Fence: corrected the cutoff from 02:00 plus margin to 00:00 UTC on D+1 (a collector stamps only D+1 after its clock passes midnight), and kept 02:00 as the job's start time. Explained that a zero count stays zero and that a crash leaves a late record handled by R7.
- Step 8 Snapshot: taken once after the fence passes. If the job restarts, it reruns the fence and the snapshot, which is still safe.
- Step 8 Wait: a committed offset moves only after its write succeeds, and a stuck partition blocks the close. The job status shows the short partition, its consumer and the offset it needs.
- Step 8 close paragraph: added that the stored snapshot offsets are an audit record, read by no live path, and used by an operator to check late records.
- Step 8 retry paragraph: replaced the reference to open item 9 with a plain pointer to the open questions.
- R3: added that replay reads only winners, and that non-winner raw copies are never read or re-enriched.
- R6: split into hard checks (ABORTED with expected and actual values, R9 applies), the diff report, and approval (a pause for an unexpected diff, ending in R7 on approval or ABORTED on rejection).
- Open item 5: added that a dropped copy can have an earlier received_at than the winner, so its day differs from the partition day.
- Checks before launch: changed 'first arrival wins' to 'first copy to claim the event_id wins' to match step 5b.
- Replaced the 'Definitions' list with a 'What this is' summary and a 'Terms' section. Each term is defined in one plain line, including log, offset, consumer, claim, ledger, day status and staging partition.
- Removed the received_at watermark for closing a day. The close now uses three parts in order: fence, snapshot of log offsets, and wait for committed offsets (decided in the Q1 and Q2 answers). The text states why offsets are used in place of timestamps.
- The fence starts at 00:00 UTC on D+1, the moment a collector's clock passes midnight, not at 02:00. The 02:00 time is now described only as the job's start time (Q12 and Q13).
- The ledger is stored in object storage, one object per received day, log partition and offset range, written before the warehouse commit. The reason the key-value store cannot hold it, its 8-day expiry, is dropped (Q3).
- Added the live-consumer stop on key-value store failure, with what lag and alarms show, and why skipping is ruled out. Also added the stuck-partition status the job shows (Q4 and Q14).
- Defined the enrichment version: the release process sets it, and each consumer runs the version it was deployed with. Replay names a version that must exist in the replay pool (Q5).
- Step 3 now says that a lost 202 leads to a resend that gets new stamps and creates a second log record, and that this is the main source of duplicates (Q6).
- Added a worked example of a dropped copy with an earlier day than the winner, in step 5b (Q15).
- Stated the duplicate-count reason in the failure table: a warehouse commit that is followed by a lost offset commit creates no second row (Q10 and the key-based upsert).
- Live writes read the day_status row inside their own transaction, and the table stores the closed mark (Q10). The step-6 text now says why a stale mark cannot be acted on.
- Replay is stated as manual, and the request interface is marked as undecided in the open questions (Q8).
- Replay step 3 says replay reads only winners and never changes which copy wins. The reason for the ledger is kept in one clause (Q16).
- Replay step 6 separates hard checks, which abort, from the diff, and from approval, which pauses and does not fail (Q18). The swap step re-reads the status row and says what happens when the check fails, and that a closed day cannot be reopened (Q7 and Q11).
- Stated that the snapshot offsets are an audit record that the live path never reads. An operator uses them to check late records (Q17).
- Removed the codes R1 to R9, the Q numbers, and the numbered open items that were cross-referenced. Each step now stands alone. Open items are unnumbered bullets.
- Merged repeated rules about retries and idempotency into the failure table, and merged the retention bullets. The Checks before launch list is kept unchanged in a separate 'Building and launching' section.
- Added the warehouse-capability check to the open questions, and the replay-compute and replay-interface items, as the brief requires. Bot traffic is still shown as open and is not decided.
- Kept every requirement from the brief. The brief's fixed requirements, the 5-minute freshness target, the 90-day rule, the 7-day retry window, and the replay constraints are all still present.

### Holes
- Q8: What triggers a replay in practice? Is it only a manual operator request, and what does the operator use to submit one (a UI, a CLI or a ticket)? (author: The brief says only that an operator must be able to rebuild one day, usually after an enrichment fix. It does not say how the request is submitted (UI, CLI or ticket). Nothing in the plan starts a replay automatically. The plan now says replay is manual, and open item 8 records the open interface question.)
