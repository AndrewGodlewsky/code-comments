## Review of dp-02 (junior-v6, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Rewrote the whole document in the skill's layout: summary, terms, live path, replay path, failure table, checks, open questions. Steps no longer refer to each other by number.
- Dedup (live step 8): the key-value value now holds the winner's ingest sequence, so a copy re-read after a crash keeps its winner decision (Q1).
- Dedup (live step 8): added the decided topic as the hop between dedup, the archive sink and enrichment. It was missing from the first version (Q2, Q5).
- Live step 9: clarified that duplicates are dropped from the warehouse path only (enrichment and loader). They are still archived, which keeps the brief's 90-day rule (Q3).
- Terms: defined ingest sequence as the log's partition plus offset, assigned at append, comparable only within a partition. Replay sorts by it (Q4).
- Live steps 12 and 13: enrichment and the loader now read and write named topics. The loader commits its offset only after a successful append. Added the restart duplicate risk as an open question (Q5, Q6).
- Live step 14: day closure is decided by the loader's clock check. Dashboards read events_clean only (Q6).
- Live step 15: the close job waits for archive completeness before comparing counts. On mismatch it writes no manifest and alerts. The retry deadline is an open question (Q7).
- Live step 10: the archive sink commits each copy once, keyed by ingest sequence, because a crash can re-deliver a copy. Found while answering Q1. Without it the archive could hold a copy twice and make winner selection fail.
- Replay step 18: removed events_late from the replay inputs. Those winners are already in the archive, and reading both would count one winner twice. events_late is used only in the close count check (Q8). This changes the plan's replay inputs.
- Added a failure table, a short checks section and open questions 6 to 8: loader restart duplicates, close retry deadline and staging cleanup after a failed replay.
- Kept every stated requirement and every open decision from the first version (bot traffic left open, rejected payloads, dedup-logic changes, client retry guarantee, sizing, archive-lag threshold). Did not choose for product.
- Step 8 (dedup): added the rule for a key-value store error or timeout. The consumer retries the same copy, does not skip it or guess, and a lag alarm fires. A timeout after a successful set is covered by rule 2. (Q9)
- Failure table: added a row for key-value store errors, and the enrichment row now says there is no automatic replay. (Q9, Q14)
- Step 10 (archive): each copy is filed under its own received_at day, with the D+1 duplicate example. (Q12)
- Step 12 (enrich): states that failed enrichment is not replayed automatically, and an operator decides. (Q14)
- Step 14 (late winners): the loader's clock is the NTP-synchronised host clock. The loader decides once per winner, just before its append. A winner checked before 02:00 stays in events_clean. (Q13)
- Step 15 (close check): the close job also waits for loader lag to clear on winners received before close. It states that each winner sits in exactly one of the two tables. It states that the check runs before any replay. (Q13, Q10)
- Step 20 (select winners): explains that the sort gives a fixed row order and does not decide winners. (Q11)
- Step 22.4 (validate staging): the row hash compares rows as a set, ignoring order, because the live partition was built by appends. This is a correction to the plan. (Q11)
- Step 24 (clean up): events_late rows are kept after a replay. A late winner can be in both tables, so they are not added together. The count check is not rerun after a replay. (Q10)
- Open question 4: notes that a late copy after the TTL can make a winner on a different day, so one event could have a winner on two days. (Q12)
- Restructured for a newcomer: added a summary paragraph and a terms list, put each step in its own order, and separated the checks from how the system runs. All stated requirements from the brief and the first version are kept.
- Step 15: the close job no longer schedules a replay when events_late has rows for D. It records a replay request for an operator instead, because the brief makes replay an operator action and step 17 needs a reason and versions.
- Step 17: added the close-job request path. The close job fills in the reason and the enrichment-manifest versions, the operator confirms or changes them, and the lock, closed-day and archive-expiry checks apply to both request paths.
- Failure table: added a row for the close job recording a replay request when events_late has rows for D.
- Step 15 and 17 wording: removed the unset phrase 'the retry deadline is open (open question 7)' cross-reference in favour of plain wording, and wrote the replay lock and request terms out in the terms list.
- Layout: reorganised the file into the required order (summary, terms, live path, replay path, failures, checks, open questions), with each term defined in one line and no change to the step numbers or to any stated requirement.
- Rewrote the whole plan once for a newcomer, keeping the order: summary, terms, live path, replay path, failures, checks, open questions. Verification is now under its own heading, separate from how the system runs.
- Summary: now says how the current system works (no pipeline today, which existing parts are reused) and why the archive is the replay source.
- Terms: added plain-language definitions for log, ingest sequence, decided topic, enriched topic, key-value store, close, lag, canary and staging table. Ingest sequence is defined as partition plus offset, comparable only within a partition.
- Live path: each step now says what it does and what it keeps, in full sentences. Dedup (step 8) is written out as sub-steps with the crash-retry and store-outage rules inline. Late winners (step 14) and close (step 15) say what each branch does.
- Step 8: kept the set-if-absent value, the same-ingest-sequence rule for a re-read copy, the offset commit after the decided topic accepts, and the store-outage retry rule.
- Step 9: merged the two statements about dropping duplicates into one: nothing leaves the archive or decided topic; only the warehouse path drops them.
- Step 10: kept the folder rule for duplicates received on another day, the atomic commit, and the once-per-copy commit keyed by ingest sequence.
- Step 15: kept the two wait conditions, the count equation, the pass and fail branches, and the open retry deadline. Removed the code references to other steps where the reader would have to look them up.
- Replay step 17: kept the three refusal checks, the requirement that they run for close-job requests too, and the fill-in of reason and versions. Stated in plain words that nothing replays on its own.
- Replay steps 18 to 24: kept every input rule, the winner sort, the duplicate-winner failure, the five staging checks (row hash compared as a set), the atomic swap, the manifest, and the rule not to add events_late to events_clean.
- Failure table: kept every row. The dedup store row now says later copies in the partition wait.
- Checks: kept all eight checks unchanged in substance, under 'How we verify it'.
- Open questions: kept all nine, including the bot-traffic decision left open with no default, and the rejected-payload proposal. Question 3 and question 4 are stated in full sentences, with the 7-day lookback and two-day-winner risk kept.
- Added: nothing new in design. The changes are wording and layout only. Every requirement, limit and number from the brief and first version was checked and kept: 100 events, 4 MB cap, 32 KB limit, 1 s to 5 min backoff, 7-day buffer, 8-day TTL, 14-day log, 90-day archive, 02:00 close, 5-minute p99 with 3-minute alert, and the per-minute canary and loader cadence.
- Length is roughly 1.3 times the working document. Most of the growth is the terms and the sentence-level steps.

### Holes
- None.
