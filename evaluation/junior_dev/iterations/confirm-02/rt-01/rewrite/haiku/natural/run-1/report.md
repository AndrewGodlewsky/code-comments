## Review of rt-01 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short summary of what this is and how the main flow goes, plus the one-sentence description of the current Postgres-polling system, which the first version did not say in plain words.
- Added a terms section that defines every name a newcomer to this stack would not know: gateway node, document service, connId, userId, rev, appliedRev, caret, seq, transformPosition and HistoryGone, heartbeat, sweep, nudge, pub/sub, sorted set, hash and EXPIRE.
- Kept the Mermaid sequence diagram unchanged, with its notes, as the deliverable.
- Replaced the separate step-by-step text with five numbered steps. Each names its trigger, what it does, where its state is and its failure, and does not repeat the diagram's order. Merged the cursor rate and idle-joiner rules into steps 1 and 2 so each is stated once.
- Corrected the state table. The highest seq per connId was listed under node memory, but the rules say the receiving client keeps it. It now sits with the client's memory row, and the node row keeps only the socket map and throttle timestamp.
- Kept the member-string exact-match rule in the presence row, because ZREM needs it.
- Cut the requirement check. It repeated the rules and the state table, so each fact now appears once.
- Merged the failure cases into one table with a Bounded by column. This covers clean close, dropped nudge, crash, empty keys, rate drop, held caret, HistoryGone, out-of-order cursors, Redis failover and node restart.
- Kept every number and limit from the brief and first version: 50 ms, 10 s heartbeat, 30 s stale window, 5 s sweep, 60 s EXPIRE, 2 s and 35 s bounds, 500-revision history, 6 nodes, 20 s pong timeout and 30 s client poll, and the 45 s limit.
- Open questions now say that none block the design and point to the Redis failover row as the one accepted risk. Nothing in the brief needed a build or rollout section, so none was added.

### Holes
- None.
