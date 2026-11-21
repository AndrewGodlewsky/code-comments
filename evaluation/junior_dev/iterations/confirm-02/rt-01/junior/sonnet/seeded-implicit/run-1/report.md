## Review of rt-01 (junior, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Replaced the vague outline with a full plan: summary, terms, diagram, numbered steps, failure table, open questions.
- Defined the Redis data: per-connection entry with a 30 s TTL, per-document index set, and one channel per document, with refresh every 10 s.
- Added the snapshot rule: subscribe first, read, then send the snapshot followed by buffered messages, so a join is never missed.
- Defined the cursor message (rev, pos, seq), the hold-until-applied rule, transformPosition and HistoryGone handling, and the seq rule against backwards jumps.
- Replaced the unclear sweeper with a rule that any serving node checks the index every 10 s and the node that wins SREM publishes leave, giving at most about 40 s to detect a crash.
- Fixed the diagram: the crashed node is Node 2 (Bob) and the leave goes to the survivor Alice. Added Bob's pre-existing state and the 50 ms server drop.
- Replaced 'Dedupe tabs on the client' with an explicit rule: one avatar per userId, one caret per user, and a user leaves when their last connId goes.
- Added a failure table and two open questions (palette size and per-user versus per-tab caret).
- Heartbeat (step 6, diagram) now rewrites entries from the node's in-memory copy, so it cannot overwrite a newer cursor, and the node memory is listed in where state lives.
- Heartbeat now also re-adds the connId to the index and republishes join if the entry had expired, so a live user wrongly swept comes back; added a Failures row and an open question for the remaining tiny race.
- Step 2 now says Alice's own join is applied as an upsert, snapshot cursors are handled like step 5 cursors, and the first cursor is sent after document load using the current appliedRev.
- Step 5 now says what the receiver deletes on leave (entry, seq, held cursor, caret), and Terms/where-state say the client keeps last seq per connId.
- Step 1 now says a reconnect gets a new connId and the old entry is removed by leave or expiry.
- Step 9 now says nothing else signals a crash and the dead user's avatar and carets stay frozen until leave.
- Step 4: added that the sender gets no echo and that a failed Redis cursor write closes the socket, as in step 1 (Q18).
- Terms and step 5: stated what moves appliedRev and that held cursors are re-checked each time it moves; added an open question about unverified other causes (Q19).
- Step 6: the rewrite is SET EX 30 GET so the node can tell an entry had expired without a separate read; said the heartbeat never publishes an older cursor (Q20).
- Step 7 and where state lives: said how a node knows its documents, what the sweep cost grows with, why the index never lists an unwritten entry, and that all Redis calls go to the primary (Q21).
- Step 3 and where state lives: defined most recently as arrival order, added fallback to the user's other connection when it leaves, and said the client stores the last cursor per connId (Q22).
- Step 1 and failures table: the client keeps its old list frozen while disconnected until the new snapshot replaces it (Q23).
- Step 9, failures table, open questions: replaced references to the brief with the required 45 s and noted that no limit is set for a vanished browser (Q24).
- Failures table: Redis-unreachable row now says an error on open or cursor write closes the socket.
- Reordered to the skill layout: summary, terms (including where state lives), diagram, numbered steps, failures table, open questions.
- Fixed the diagram's confusing tail: removed the parenthetical about reading Alice as a second user and added Carol, a user who stays on Node 1, as the receiver of Bob's leave after the crash.
- Merged the subscribe-when-local-socket rule into the Channel term and removed its repetition from step 1.
- Merged the 'client replaces its map and stored seq' statements from step 2 and step 5 into step 2 only.
- Moved the pong-timeout rule into the heartbeat step, where it applies; cut the repeated 'same rule as ops' wording.
- Replaced 'cleaned up lazily, see step 7' in the Index term with a plain statement that the sweep removes stale ids.
- Clarified the crash timing in step 9 as a breakdown (10 s refresh gap, 30 s expiry, 10 s sweep) and kept the 45 s requirement.
- Added in step 7 that the primary applies commands in order, the reason a just-written entry is never swept as missing.
- Trimmed small repetitions (client no-echo, cost wording) while keeping every number, limit, key name and rule from the first version.

### Holes
- None.
