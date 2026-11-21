## Review of rt-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a short opening paragraph stating what the plan adds and what it does not change, so a reader sees the scope first.
- Added a Words used section that defines gateway node, connId, userId, revision, caret, seq, TTL and pub/sub for a reader who does not know the project.
- Added a table of where each piece of state lives, who writes it, what refreshes it and what removes it. The original said 'make clear where each piece of state lives' only in a single line about entries having a TTL.
- Gave concrete values: 30 s TTL on connection and cursor keys, pong refresh every 10 s, 5 s sweep, and a worked bound of 35 s from crash to removal. The original gave no numbers. These are plan values and are flagged as such.
- Named the Redis structures: the connection index hash, the conn key, the cursor key and the presence channel. The original only said 'register presence' and 'refresh'.
- Corrected the crash section. The original sent the leave from Node 1 to Alice without saying who left, and it did not show Bob's cursor being removed. It now shows the sweep, the removal of Bob's index row and keys, and the leave for Bob.
- Added the missing parts of the join: Bob is already in the document on Node 2, the snapshot includes idle users' last cursors, and Bob receives Alice's join.
- Added the revision hold to the cursor step, so the diagram shows that Bob's client holds the caret until it has applied rev 42.
- Added the 50 ms per-connection drop to the cursor step, and the leave-only-if-last-connection rule to the clean-leave step.
- Turned the original terse notes into explained steps and a separate set of client rules for seq, no backwards jumps, the revision hold, transformPosition and HistoryGone. The original notes listed these only as topics.
- Clarified 'Dedupe tabs on the client' as a per-user list and one caret per user, using the most recently arrived cursor. The brief does not specify carets for a user with two tabs, so this is a choice the plan makes and it should be confirmed.
- Added a Limits section that states pub/sub is best effort and that a missed leave can leave a stale entry until reopen. The original did not mention this.
- Stated that the old Postgres presence table and its 30 s polling are retired, and that the edit path, document service and load balancer are unchanged, as the brief requires.
- Kept the Mermaid sequenceDiagram and the notes format. Removed the use of semicolons and braces inside diagram messages so the diagram parses reliably.
- Added a plain-language "How the system works today" section so a reader new to the project can follow the rest.
- Expanded the glossary to define the terms the plan relies on: WebSocket, Redis, hash, TTL, pub/sub, script, ping/pong, heartbeat, sweeper, idempotent, snapshot, and transformPosition/HistoryGone.
- Clarified the table cells, for example that the index row is not renewed and is only checked by the sweeper, and that Cursors never reach Postgres.
- Added an explicit step that the node subscribes to presence:{docId} before reading the snapshot. The original did not say this, so a join or leave arriving during the snapshot read could be missed. This is a small behaviour clarification to the plan, not a new design choice.
- Noted that duplicate joins are harmless because the list is keyed by userId, including the join Alice's own node receives.
- Stated the clean-leave rule directly: the script reports whether other connections remain, and a leave is published only when none remain.
- Spelled out that a newer accepted cursor from the same connection drops any older held cursor, in the client rules.
- Clarified how the seq rule and the one-caret-per-user rule interact.
- In the diagram, changed the cross-arrow to A-x N1 with a space, made message labels plain English (for example, a script step is labelled as a script), and split the crash sweep into explicit steps with the leave published on the same node. Intent and participants are unchanged.
- Added a plain-language opening that says what the two features are and what the plan does not change.
- Added a short 'How the system works today' section that explains WebSockets, the load balancer, and the edit path in plain terms.
- Rewrote the glossary entries to say what each term means in this plan, and expanded hash, TTL, pub/sub, script, sweeper and idempotent so a reader new to Redis can follow them.
- Reworded the state table's cells in plain language without changing any owner, refresh or removal rule.
- In the sequence diagram, replaced the crash-path reply that appeared to come back from Redis after the publish with a clearer label showing that Node 1 receives its own leave message through its subscription.
- Rewrote the step descriptions as shorter, plainer explanations, and made the crash timing arithmetic explicit (30 s TTL plus up to 5 s sweep wait, inside the 45 s requirement).
- Restated the client rules with the same logic and clearer sentences, including the tab rule and the held-cursor behaviour, without changing any rule.
- Kept all headings, the table, the Mermaid sequenceDiagram, and the limits, and did not change any design decisions or values.

### Holes
- None.
