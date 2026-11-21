## Review of rt-01 (junior, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Step 1 diagram: the snapshot arrow now says it is the JOIN script's return value, not pub/sub (Q1).
- Added definitions of a Redis script, rev, appliedRev, transformPosition and HistoryGone under Where state lives (Q2, Q6).
- Join note: node B holds pres:doc1 events for the joining connection until after the snapshot is sent, then sends them (Q3).
- Heartbeat sweep note: says what is compared (Redis users and connId-to-seq cursors against a per-socket record of what was sent) and that every node runs it on its own timer (Q4).
- Added a short Reconnects section: new connId and a full-replace snapshot on WebSocket reconnect, and an immediate read-and-compare when a node resubscribes (Q5).
- Cursor path: a failed or slow CURSOR script call drops the update with no error to the client and no retry (Q7).
- Cursor fan-out: the event carries connId and userId, and node A sends to the same user's other local sockets. A cursor is accepted only from a connection that has opened that document (Q8).
- Fixed the cursor fan-out: a node sends a cursor event to all its local sockets of the doc except the sender's connId, not only to the sender's other tabs (Q9).
- Added the node's last cursor (seq, rev, pos) to the node-memory row and to the diagram, so REFRESH has a source (Q11).
- Reworded the Alice re-send note as the client's own 10 s timer, separate from the server heartbeat (Q12).
- Added JOIN failure handling: the doc loads anyway, the socket is marked not joined, and JOIN is retried on the 5 s tick (Q13).
- Corrected the timing budget to show how 30 s and 35 s are reached and that 45 s is the brief's limit (Q14).
- Added to the crash step that Redis drops the dead node's subscriptions itself, that Alice's reconnected tabs do not make her show twice, and that userGone is false if she is live elsewhere (Q15).
- Added an Open questions section for the unconfirmed source of name and avatar (Q10).
- Added a short account of how presence works today at the top of the summary and cut the summary to two short paragraphs
- Added a Terms section: gateway node, connId/userId, localSockets, Redis script, ZSET/HASH, rev/appliedRev, transformPosition and HistoryGone, seq (answers Q2, Q6)
- Moved the old timing table, reconnect notes and per-step failure notes into one 'When things fail' table, and added the lost-message, JOIN-fail and CURSOR-fail rows
- Merged duplicate rate-limit text: the 60 ms client spacing now appears only in Rules, and the diagram message no longer repeats it
- Removed the separate 'Unchanged' and 'Volume' bullets: volume merged into Rate limit, unchanged merged into a Rollout section that keeps the Postgres retirement apart from how the system runs
- Removed the 'Cursors are ephemeral' bullet because the summary now states it once
- Shortened and merged diagram notes (heartbeat and sweep step retitled, Alice's 10 s client timer moved inside it, crash note trimmed) without dropping facts
- Kept every requirement and number from the first version: 50 ms, 60 ms, 2 s, 45 s, 10 s, 20 s, 30 s, 5 s, 90 s, 500 revisions, Redis TIME, ZADD upsert
- Kept the unconfirmed profile lookup as the single open question
- Added the answers' content to the places they belong: snapshot as script return value, held events on join, per-socket compare, cursor fan-out to all local sockets except the sender, not-joined retry, node crash and reconnect behavior

### Holes
- Q10: Where does node B get Bob's userId, name and avatar when he opens doc1? Is it from the session cookie, or another lookup, and what happens if that lookup fails? (author: userId comes from the session (checked in the gateway doc). The docs do not say where name and avatar come from, or what happens if a lookup fails. I added an open question with a suggested fallback to userId and a default avatar, but have not confirmed it.)
