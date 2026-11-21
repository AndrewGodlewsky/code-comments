## Review of rt-01 (junior, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Named the Redis keys per document in the terms, and noted that the diagram's presence:doc names are shorthand for them.
- Added leases to the key-expiry (EXPIRE) refresh. Without it, leases stayed in Redis for good if no node survived.
- Heartbeat now runs the join steps again when its lease is missing, so a node that stalled for more than 30 s comes back instead of staying unlisted.
- Join now runs the sweep before it reads the snapshot, so a crashed node's users are not listed when no surviving node was sweeping.
- Clients apply presence events by presence_ver: they ignore events at or below the snapshot's version. The node forwards events to a socket only after that socket's snapshot.
- Held cursors are drawn only if their seq is still above the last seq shown, and a newer seq replaces a held one. This closes a backward-jump case where an older held cursor was drawn after a newer one.
- Leave and sweep also raise presence_ver, so every presence event carries a version.
- Every browser in the document answers hello, not only Ben.
- A node that resubscribes to Redis sends its local sockets a fresh snapshot, so presence events lost during the outage are recovered.
- Stated that cursors never reach Postgres or the document service, and that the 40 s bound is measured from the crash.
- Added a state table saying where each piece of state lives and what refreshes or removes it, and a failure table. The Postgres polling is named as the thing this design replaces.
- Changed: Terms: presence_ver now rises only for each published join or leave, and the snapshot term now covers rejoin and resubscribe (Q10, Q12).
- Changed: Step 1 Join: the join script counts entries inside the same script and publishes only when it is the user's first (Q9); the snapshot is one atomic read with the version (Q10); presence and cursor events are forwarded only after the snapshot (Q11); a version gap asks for a new snapshot and a snapshot always sets the version (Q10).
- Changed: Step 3 Move a caret: the browser sends its latest position at the end of the 50 ms window (Q14); the cursor write only happens if the connId still has a lease (Q11); the browser drops a cursor for a connId not in its list (Q11).
- Changed: Step 4 Heartbeat: the rejoin runs the join steps, which end with hello, and the snapshot drops held and shown carets (Q12).
- Changed: Steps 5 and 6: presence_ver is raised only when a leave is published (Q10).
- Changed: Diagram scenes 1 to 5 follow the same rules: a single presence_ver raise per published event, an atomic snapshot read, cursor writes that check the lease, and the leave in the lost-node case (Q9, Q10, Q11).
- Changed: Where-state-lives table: presence_ver row and held or shown caret row updated (Q10, Q12).
- Changed: Failure table: the stall row now says the node's own browsers see the leave and the user is missing for up to 10 s (Q13); the subscription row now says the node resubscribes and sends a snapshot and hello (Q12, Q15).
- Changed: Open questions: added the Redis client event for a lost subscription, which has not been checked (Q15).
- Changed: Step 1 now says every snapshot is followed by hello (from the join, a gap, a rejoin or a resubscribe), instead of hello only after the join. A gap snapshot no longer leaves carets hidden until each user moves.
- Changed: The Snapshot term now lists the version-gap case and states that every snapshot is followed by hello.
- Added a short 'today' paragraph to the summary, as the skill requires for a change to an existing system: Postgres table, 30 s polling, nightly cleanup, no cursors.
- Summary cut to three sentences: what it is, the main flow, why it is shaped that way.
- Defined every term a newcomer would not know: WebSocket, pub/sub, Lua script, Redis TIME, key expiry, the four document keys, lease, snapshot, hello, rev, appliedRev, transformPosition, seq. Each is one line.
- Snapshot rules (replaces list, stored cursors and version, drops held and shown carets, hello follows) were stated in the terms, steps 1, 4 and the table. Now stated once, in step 1.
- The hello rule (every snapshot is followed by hello) and the version-gap rule were merged into step 1 and step 2, and the failure table keeps one row for the gap case.
- The browser's cursor-receiving rules were moved out of the diagram notes into step 3 as an ordered list (a to d), so the diagram notes point to them instead of repeating them.
- Step 3 now explains why a reconnect is never dropped by the old seq.
- Step 4 heartbeat now says the key expiry sits in the same script, and that a missing lease reruns the join steps.
- Step 5 sweep keeps the 'only the call that removes it continues' rule and the no-socket case.
- Step 6 and step 7 state the 2 s leave target and the 45 s limit explicitly, with the 40 s derivation kept.
- Step 7 added the statement that nothing stays in Redis for good, using key expiry.
- Diagram: removed semicolons and the '->' arrow-style text inside messages so the Mermaid parses; shortened notes that repeated step rules; Scene 3 heartbeat folded into one message with its EXPIRE; Scene 5 sweep result moved to a note over Redis.
- Diagram: the node subscribes and sweeps before the join, and the snapshot read is one atomic read, as in the current design. The browser-side HistoryGone note was dropped from the diagram and kept in the failure table.
- Failure table: added the Q13 trade-off (the live node's own browser also drops the user until the next heartbeat), added a version-gap row, and kept every other row, reworded to match the steps.
- Open questions kept unchanged in substance (colour, two carets per user, the Redis client event that reports a lost subscription, unverified).
- Removed codes such as R3 or Q7 from cross-references. Steps refer to each other by name, not by code.
- No stated fact was cut: 10 s, 30 s, 40 s, 45 s, 50 ms, 2 s, 120 s, 500 revisions, six nodes, the edit path, Postgres and load balancer not changed, cursors never written to Postgres or the document service, Redis pub/sub stores nothing.

### Holes
- Q15: How does a node know a Redis subscription was lost so that it resubscribes and sends a fresh snapshot? What triggers this? (author: The design relies on the Redis client reporting that the subscription dropped, and on the node then resubscribing and sending snapshots. The gateway doc does not name the Redis client library, and I have not checked which event it gives for a lost subscription. What the node does after that report is decided: resubscribe, send a snapshot, publish hello. This is listed as an open question.)
