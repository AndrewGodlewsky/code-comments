## Review of sync-02 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a "Background for readers new to this system" section that explains Postgres, change_seq, tombstones, SQLite and WAL mode, keyset pagination, HTTP status codes, and what Wi-Fi means.
- Explained the anchor in plain terms: pages cover the state at read time, and the change feed covers everything after the anchor.
- Defined the inactive table and explained atomic pairing, single runner and idempotent apply in plain words.
- Dispatcher (step 3): status paused_wifi was not covered, so a paused download would have started a fresh download and discarded its progress. It now resumes at step 11. Added an explicit 'otherwise, do nothing' branch.
- Listed resync_pending as a flag on top of downloading or paused_wifi, not as a status.
- Step 4: a resync that starts off Wi-Fi now records paused_wifi and keeps the active table served, instead of going to a download that needs Wi-Fi. Step 10 and step 11 were updated to match, including the case of no stored anchor.
- Step 7: stated that a delete removes a row only under the same change_seq rule, and why the catch-up can take several batches.
- Step 9: the 410 path now says the replacement download waits for Wi-Fi.
- Step 1: explained the purge horizon in plain terms.
- Renumbered the open questions and assumptions to Open questions 1-2 and Assumptions 1-4. The old numbering ran 1-6 and made step 9's reference to 'Open question 3' point to an assumption. The reference now reads 'Assumption 1'.
- Made the retry policy wording explicit: 5 attempts in total, waits of 2, 4, 8 and 16 s, and the budget resets when a new trigger starts a run.
- Added a note that the existing client layer handles token refresh, and clarified that 401 is covered by Assumption 2.
- Added plain-language definitions for cursor, purge horizon, and the four statuses, so a reader new to the system can follow the steps without prior context.
- Defined active, staging and inactive generations in plain terms, and stated that staging is empty or unused when no download runs.
- Step 5 now sets status to catching_up in the same transaction as the last page. The draft used catching_up in steps 3, 8 and 11 but never said where it was set.
- Step 7 now checks Wi-Fi before each batch, not only at the start. The draft left catch-up on cellular without a rule.
- Step 6 now says where a resumed download restarts (step 5 if pages remain, step 7 if all pages are saved), instead of always resuming at step 5.
- Retry policy now states the wait sequence and the attempt count together (four waits, five attempts in total), so the schedule is not misread.
- Step 1 explains the purge horizon in one sentence, and step 2 separates the catalogue file from the settings database more clearly.
- Restated the reasons for step 7 and the atomic-pairing rule in shorter sentences. Behaviour, steps, open questions and assumptions are unchanged, and open question 1 is still undecided.
- Added a plain-language glossary for terms a new reader would not know: transaction, upsert, idempotent, and the HTTP status meanings.
- Explained the retry timing in words (2 s before attempt 2, then 4 s, 8 s and 16 s) instead of listing the waits as a bare sequence.
- Stated in the idempotent apply rule that a delete follows the same change_seq rule and does nothing when the row is already absent, which was implied before.
- Reworded the anchor definition to say that pages alone can miss later changes and that the feed from the anchor covers them.
- Reworded the step 7 rationale so it says why the anchor guarantees no gaps, rather than asserting it.
- Added one-line descriptions of each status in sync_state, since a reader needs them to follow the steps.
- Described the device database and WAL mode in the background section so the separate catalogue file is clear.
- Made the generation roles explicit (active, staging, inactive) and explained that the pointer in sync_state records them.
- Reworded step 8's crash case so it explains why the swap re-runs safely after a kill.
- No change to the plan's logic, step order, failure handling, open questions, or assumptions.

### Holes
- None.
