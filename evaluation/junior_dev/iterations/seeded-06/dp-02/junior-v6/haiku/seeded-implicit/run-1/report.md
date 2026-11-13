## Review of dp-02 (junior-v6, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Rewrote the whole plan in the skill's order: a summary, then terms, then the live steps, then the replay steps, then a failure table, then open questions.
- Added the fixed requirements the first version left out: batches of up to 100 events over HTTPS, 202 only after durable storage, the three malformed-event rules, 1 s to 5 min exponential backoff, the 7-day device buffer, the 14-day log retention, and the 90-day archive rule covering duplicates too.
- Added the rule that an event belongs to the UTC day of received_at, which decides both its partition and its replay.
- Stated the live dedup rule: first copy wins, keyed by event_id alone, with a KV TTL longer than 7 days.
- Added the replay rules the first version left out: operator-started, closed days only (closed at 02:00 UTC the next day), its own dedup state that never touches the live KV store, a staging table, an atomic partition swap, no half-rebuilt day, and no slowdown of live ingestion.
- Added the 5-minute queryable target to the summary and the monitoring step.
- Kept bot filtering open, as the brief requires, and did not choose for product.
- Added a failure table covering each step's failure case.
- Added open questions for the gaps the brief does not decide: reject bucket handling, the crash window between the KV write and the warehouse load, cross-day replay dedup, late events after close, reader outages longer than 14 days, the KV stored value, and the lag alert response. No new mechanism was added for any of them.
- Terms: added log position, set-if-absent write and replay state, and defined each archive file as one UTC hour of received_at (Q10, Q11, Q13, Q14).
- Step 3 (Archiver): each event goes to the archive file for the UTC hour of its received_at, and the Archiver moves its log position only after the file is written (Q11, Q14).
- Step 4 (Live processor): the check-then-write became one set-if-absent write with the TTL, so two instances cannot both win the same event_id (Q10).
- Step 4 (Live processor): reads and loads in small groups in log order, and moves its log position after each group is loaded (Q9, Q11).
- Replay step 2: replay state is built fresh for each run, held by the replay job, and discarded when the run ends (Q13).
- Failure table: added rows for two Live processor instances, a Live processor crash before or after the load, and an Archiver crash (Q10, Q11, Q14).
- Open questions: added whether the KV store supports set-if-absent with TTL (Q10), and noted that the reason for the 02:00 UTC close is not given (Q12).
- Step 2: the collector now attaches the request metadata (client IP and User-Agent) to each accepted event, and states that the 202 waits for the raw log's acknowledgement (Q15, Q16).
- Terms: added Request metadata and Durably stored, and defined received_at as stamped on arrival (Q15, Q16).
- Step 3: added the rule that an hour's file is complete once the Archiver has read past the end of its hour, and that the archive keeps events as received with their request metadata (Q17).
- Step 4: the processor now retries a failed group without re-checking its KV keys, and waits when the KV store is down instead of loading or skipping (Q18, Q20).
- Replay step 2: defined completeness as all 24 files read and all first-copy rows staged, and each run uses its own staging table (Q19).
- Failure table: added rows for a failed warehouse load, a KV store outage, an Archiver behind at the 02:00 close, and two replays of the same day (Q17, Q18, Q19, Q20).
- Open questions: added archive completeness and log order, whether the client IP may be stored, and whether a second replay should wait (Q15, Q17, Q19).
- Removed the duplicated restatement of the live flow from the summary and merged the two rules about KV checks into step 4, to keep the file within its length budget.
- Added an opening paragraph that says what the pipeline is, walks the main flow from start to finish, and gives the reasons for its shape (client safety, full archive, replay isolated from live state). Kept the existing system description: the raw log, object storage, KV store and warehouse already exist and only the collector is new.
- Added one-line definitions for the Archiver, the Live processor and the reject bucket, since the steps use them; the terms list otherwise kept every term from the earlier version and defined each in plain words.
- Rewrote each live and replay step so it stands alone: what starts it, what it does, what keeps its data, and what happens when it goes wrong. Moved the group-load failure, crash and KV-outage handling from the step prose into the step itself, with the same rules as before.
- Replay step 2 now says the replay state is built fresh per run, holds only that run's event_ids, and is discarded at the end. Step 3 now says new events normally do not add to the closed day, and points the late-event case to Open questions instead of stating it as settled.
- Kept all 18 rows of the failure table, reworded in plain words; removed the separate step-numbering references so each row reads on its own.
- Kept all 14 open questions. Merged the Archiver-behind and unordered-log questions with the question of how an hour file is written and sealed, since they share one cause. Removed the earlier version's round-by-round answer codes and the Q/A references from the text; no requirement, limit, number or rule from the brief was dropped (including the 100-event batch, 32 KB limit, 1 s to 5 min backoff, 7-day buffer, 90-day archive, 14-day log, 24 hourly files, 02:00 UTC close and 5-minute goal).
- Plan behaviour is unchanged. No mechanism, lock or retry rule was added beyond what the earlier version and the answers already contained.

### Holes
- Q3: What happens to events in the reject bucket? Does anyone look at them or reprocess them, and does the SDK learn its batch was partly rejected? (author: The response lists the rejected events and clients never retry them, so the SDK does learn which events were rejected, and it does not resend them. Who reads the reject bucket, whether anything reprocesses it, and how long it is kept are not specified. Listed as open.)
- Q8: What do you do when the consumer lag alert fires, and which consumers does it cover? What happens to events if the Live processor is down or lagging for a long time? (author: The brief does not say what on-call does when the consumer lag alert fires, or which consumers it covers. Checked: if the Live processor is down, events stay in the raw log for 14 days. After 14 days they are gone from the log. Whether the archive still has them depends on the Archiver, which the brief does not cover. Listed as open.)
- Q12: Why does a day close at 02:00 UTC rather than at midnight? What is the 2 hours for? (author: The brief sets the 02:00 UTC close but gives no reason for the two hours. I do not know why it is two hours rather than midnight. The plan states the rule as given, with no reason. The related case, live events arriving after 02:00 UTC, stays open.)
- Q17: How does the Archiver write an hourly file while events for that hour are still arriving? When is a file complete and readable, and is every hour's file complete by the time a day closes at 02:00 UTC? (author: The brief does not say how an hour file is written while events still arrive, when it is sealed, or that log order matches received_at. The plan now says an hour's file counts as complete once the Archiver has read the log past the end of that hour. I do not know whether that guarantees every hour is complete by the 02:00 UTC close. It is listed as open, with the case where the Archiver is behind at the close.)
