## Review of rt-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Replaced the one-line notes with a self-contained explanation: terms (connection vs user), a state table naming the exact Redis keys, node memory and client memory, and what writes, refreshes and removes each.
- Defined the join snapshot: subscribe first, then a Lua script drops expired entries, registers the connection and returns users plus stored cursors. Idle users' carets come from the stored last cursor, because pub/sub stores nothing.
- Specified the cursor path: 50 ms client send, silent per-connection server drop, no document service or Postgres, and a periodic re-send so the stored revision stays inside the 500-revision history window.
- Spelled out the receiver rules in order: seq check against backwards jumps, hold until the revision is applied, transformPosition on the applied revision, hide on HistoryGone, re-transform as revisions advance.
- Defined multi-tab handling: per-user join and leave flags, so a user shows once and leaves only on their last connection, and per-connection carets.
- Gave concrete timings and the arithmetic: 10 s refresh, 30 s expiry, 5 s sweep, 35 s worst case under the 45 s limit, 60 s key TTL so nothing stays in Redis for good.
- Explained the crash path: surviving nodes sweep atomically, safe to run concurrently, and each leave is published once.
- Redrew the diagram with labelled steps and notes at the points where state changes. It now shows Bob already present on another node, the subscribe-before-snapshot order, the throttle, the seq and revision checks on the receiver, the periodic refresh, a clean leave, and a Node 2 crash seen by Alice. Alice rejoins before the crash so someone is left to observe it.
- Added a closing timings table and noted that Edits, the load balancer and the document service are untouched, and that Postgres polling is removed.
- Replaced the awkward in-diagram note about Alice rejoining with a real 'open doc again' step, and added a sentence before the diagram explaining why (Node 1 needs a socket on the doc to be subscribed and sweeping).
- Moved the diagram under its own 'Sequence diagram' heading, before Timings.
- Stated that join drops expired entries by publishing leave, as sweep does, and that sweep removes entries from all three keys.
- Clarified that the cursor script publishes only when it stored the cursor (seq newer).
- Named the refresh script and made the heartbeat paragraph clearer about what it does.
- Numbered the join steps and reworded the explanation of why subscribe-before-snapshot loses no events.
- Clarified the rate-limit row and the idle re-send rule ('since the last send').
- Minor wording simplifications throughout (for example 'applying one twice is harmless' instead of 'idempotent').
- Defined 'node' in the terms list and noted users are usually on different nodes.
- Reworded the state table: cursor row says 'newer than the stored one'; events row says written by the Lua scripts; sockets row says 'Open sockets'.
- Turned the loose bullets after the table into a titled list of rules and named the three keys explicitly, and explained that Lua scripts run atomically in Redis.
- Explained why subscribing before the snapshot is safe (an event may appear twice, harmlessly) and added that the client sets lastSeq from the snapshot.
- Split the Cursor section into client and node behaviour with a short list, and gave rev and seq clearer definitions.
- Clarified rule 4 of receiving a cursor (move drawn carets forward with transformPosition) and the heartbeat wording (connections that answer).
- Rewrote the diagram intro to state the starting situation and the full scenario in order.
- Changed 'Otherwise the cursor script stores...' wording to say the script stores and publishes only if seq is newer, avoiding repetition.
- Diagram and timings table unchanged.

### Holes
- None.
