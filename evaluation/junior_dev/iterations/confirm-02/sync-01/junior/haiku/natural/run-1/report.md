## Review of sync-01 (junior, author haiku, natural)

Rounds: 5. Ended: teachback-correct.

### What changed
- Diagram: the applied-changes lookup now uses (device id, change id), and the retry branch matches it.
- Diagram: an accepted upload sets the local version to 6 before the download, so seq 101 is a no-op for Phone A (Q4).
- Diagram: the conflict note N2 is described with a new id and the title from N, and the conflict result includes N2's id (Q7).
- Diagram: Phone B's final apply step now says N becomes A2 and N2 is added together (Q2, Q3).
- Where state lives: outbox state (queued, sending) is defined, and the device id source is stated in applied_changes (Q1, Q5).
- Upload rules: sending rows are reset at the start of a sync, and a server error stops the batch with partial results (Q5, Q6).
- Upload rules: the conflict title and id source are stated, and a conflict result carries N2's id (Q7).
- Download rules: a higher version replaces the local body even with a pending row, and the pending row keeps its body and later conflicts (Q2, Q3). Own accepted changes are a no-op by version (Q4).
- Failure table: added the server error on one change, and the cut-off after upload rows, and tied the response-lost row to (device id, change id) (Q1, Q5, Q6).
- Open points: added the in-flight edit conflict, title edits not synced, and device ids trusted as sent (Q8, Q1).
- Outbox states changed to queued, sending and sent, with the rule that edits collapse only into a row that has never been sent (Q10). Previously a lost-response row could collapse with a new body and silently lose that body.
- Upload rules: stated the sync triggers and the batch contents, with oldest rows first and repeated batches until none wait (Q9, Q14).
- Upload rules: the server locks the note row during the base check and write, so concurrent uploads to one note serialize (Q15). Added a failure row.
- Accepted result sets the local version only when no other row for the note is pending. This stops local N diverging from the server when an edit is made during sending (Q16). Diagram label updated to match.
- Server error handling: rows with no result become sent and are retried at the next sync. Stated that nothing stops a change that always fails (Q11). Added an open point.
- Download rules: pages are requested in the same run until a short page, and the own-change no-op now covers the case where the version was not set (Q14, Q16).
- Download rules: stated that until a page applies the phone shows its local copy, and edits become conflict notes if the server has moved on (Q12).
- Failure table: rows described as sending and sent instead of queued, and a row added for concurrent uploads to one note.
- Open points: added the retry-forever gap (Q11), and reworded the per-note order and in-flight edit points to match the new states (Q13).
- Diagram: a dropped download now ends the run. The retry is shown at the next sync run (60 s timer, reconnect or foreground), not immediately (Q17).
- Diagram: the download page for N2 and the apply step now show N2's title and version from its entry (Q22).
- change_log: each row now carries the note's title, because a download entry must give a new note's title (Q21, Q22).
- Download rules: a fresh install reads from seq 1, and an entry with no local row creates one from its title, body and version (Q21, Q22).
- Download rules: a dropped download ends the run, and the next run restarts from the upload step (Q17).
- Upload rules: a conflict result does not store N2's id; the download is the only path that brings N2 to the phone (Q18).
- Upload rules: changes in a batch are checked in order against the version left by earlier changes in that batch (Q20).
- Failure table: the dropped-download row now says the run ends and the fetch repeats at the next run (Q17).
- Open points: added that creating a note from a phone, and a change for an unknown note id, are not designed (Q19).
- Diagram: moved the lost-response branch into the upload step as an alt in place of the normal response, so it no longer follows an accept the phone never received. The run ends there, the retry comes in the next run, and no download runs in between (Q25).
- Diagram: added a note that Phone A's cursor is 101 after its download, and that seq 102 (N2) reaches it on its next download (Q27).
- Upload rules: the batch response gives one result per change, in order, with a server error as an error result. Dropped or cut responses give no result. Both leave rows with no result marked sent (Q24).
- Upload rules: added that a retried change returns its stored result, the same conflict with the same N2 id, and creates no second N2 (Q26).
- Download rules: a new edit's base is the last applied version. A conflict result does not carry the server version, so the phone learns version 6 only from an accept result or a download (Q23).
- Download rules: restored the line that the stale state lasts as long as downloads fail, with no timeout, and that each edit burst can add a conflict note. The earlier round recorded this, but the text did not have it (Q12).
- Download rules: entries are applied in seq order, and the version check alone is enough to decide each one (Q28).
- Failure table: the lost-response row now says the run ends, so no download runs before the retry (Q25).
- Rewrote the whole document into the skill order: summary, terms, sequence diagram with notes, where state lives, how it runs (numbered steps), failure table, open questions.
- Diagram: the lost-response retry is an alt in sync run 2. Its server lookup comes before any lock or base check (Q32). Phone B's download is shown retrying at the next run, not the same run (kept from round 3).
- Unified the no-result rule: rows with no result stay sending until the next run marks them sent. This replaces the earlier mix of 'marked sent' and 'stays sending', which contradicted itself (Q33).
- Step 2: stated that a failed upload or download ends the run with no retry inside the run, and that the next trigger starts at the upload step (Q33).
- Step 3: stated that a sent row and a queued row for one note go out oldest first, both at base 5 when nothing has been applied (Q30).
- Step 4: stated that the accepted-result version rule still applies when a newer row is pending, and that the body is never changed (Q29).
- Step 5 and open questions: a pending edit can be shown over by a download and then conflicts as its own note, and the UI question is left open (Q31).
- Merged the download-failure and stale-state rules into step 5 and cut the repeated statements about triggers, conflicts and retries.
- Defined the terms a newcomer needs: server version, base version, change id, device id, outbox, change log, cursor, applied_changes, conflict note, single-flight lock.
- Kept every stated number and rule from the brief and first version: 100 rows per batch, 500 entries per page, 60 s trigger, version + 1 per accept, conflict title, no diffs, collapse rule, original base kept, device id sent once per request, out-of-scope items.
- Summary cut to three sentences and moved to the top, saying how the current local-only system works, what the server adds, and why reads and edits never wait for the network.
- Added a Terms section with one plain line per term, including SQLite, sync run, upload batch, download page, result, note lock and conflict note, so a newcomer does not need the stack. Terms that were only defined inside rules were moved here and not repeated.
- Moved the sequence diagram after the Summary and Terms and placed its notes directly after it. Kept the same flow, with the lost-response branch as an alt, the run 2 retry, the Phone B conflict and the dropped download that retries at the next run.
- Diagram labels were tidied: semicolons removed, and the local version and cursor steps made explicit. Diagram facts were not changed.
- Merged the separate Upload rules, Download rules and Apply-results rules into the numbered steps, so each fact is stated once in the place a reader would look for it. The old step 4 (apply results) became its own step under How it runs.
- Removed the duplicated cross-references and codes (such as step 3a, R3, Q7) and wrote each step to stand alone.
- Kept the brief's fixed requirements in full: local-first edits with no network wait, collapse of repeated edits to one change with the original base, full body with no diffs, server version and change log with increasing seq, the sync triggers, the 100-change batch and 500-entry page limits, the conflict rule with the (conflict) note, retry idempotence, and no skipped or missed changes after an interrupted download.
- Kept every fact from the first version: the starting state (both phones at version 5 offline), the state definitions for notes, outbox (queued, sending, sent) and sync_cursor, server notes, change_log and applied_changes, all failure-table rows, the upload and download rules, the fresh-install rule, and the open points on retention, cross-note ordering and out-of-scope items.
- Kept the answered facts from the later rounds: the (device id, change id) lookup before any base check or lock, the lock on note N, the sending-to-sent change at the start of each run, the stored result returned for retries (including the same N2 id), the cursor jump on Phone A, the no-op for the phone's own accepted change, and the version-guarded apply.
- Added the fresh-install rule (cursor 0, reads from seq 1) and the rule that a download with a higher version replaces the body even when a row is pending, with the pending row keeping its own body and base.
- Kept the open questions on creating notes, repeated server errors, the in-flight edit walkthrough, a download replacing a pending edit, title edits and device ids. Each open question is stated plainly, with no invented reason.
- Left out details that the plan does not need yet: the alternative conditional update for the note lock, and the exact wording of answer-only explanations. These stay in the report, not in the file.
- Dropped repeated wording and merged the duplicate statements about partial results, retries and local-only reads into single rules. The length is about 1.4 times the first version, within the target.

### Holes
- Q8: The outbox stores only a full body, but N2 is titled from the original title. Are title edits synced, and where is the title carried in a change? (author: The brief does not say whether title edits sync. This design carries only the body in a change, so title edits are not synced. The conflict title uses the server's current title, which is the only title the design has. Added as an open point, not decided here.)
- Q11: What does the phone do with the error it gets back, such as retry timing or telling the user? How does it stop failing forever on the same change? (author: The phone marks rows with no result as sent, and the next sync sends them again, so a server error is retried at the next sync run. Nothing in this design stops the retry. A change that always fails is sent on every sync. The design has no backoff, no give-up rule and no message to the user, and the brief does not ask for them. I do not know which server errors are transient. Added as an open point.)
- Q19: The server lock on note N is held during the check and write. How does the server treat a change for a note id it has never seen, or a first-ever note created on a phone? Where does a new note get its server version and who creates it? (author: The design has no path that creates a note on a phone, and the brief covers only edits to existing notes. I do not know what the server should do with a change for a note id it has never seen, or who assigns a first version to a new note. A reasonable guess would be a server error, which retries on every sync, but that is not decided here. Added as an open point.)
