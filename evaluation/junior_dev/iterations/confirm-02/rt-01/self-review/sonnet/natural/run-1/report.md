## Review of rt-01 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a Summary section explaining the overall mechanism (shared Redis state, one pub/sub channel per doc, expiring entries) before the detail.
- Defined terms up front: doc, connId, userId, rev, appliedRev, and the cursor fields n, rev, pos, ts.
- Explained first/last flags, seq, and why ZADD XX is used, in plain words.
- Fixed the confusing diagram setup line (Alice 'tab a1, c1') and made Carol's setup explicit; the diagram's 'before' note no longer says 'and doc'.
- Clarified that Bob's client, not the node, drops his own join event by seq.
- Renamed 'Crash' to 'Node crash' and explained the 35 s worst case as 30 s plus 5 s; clarified the failover rule and the 'Redis failover' timing row.
- Clarified that the 50 ms check is against the previous accepted update, and that the load figure of 17 per second comes from the 60 ms client limit.
- Minor wording tightening throughout; no design decisions changed.
- Rewrote the summary opening to say Redis is already deployed and is the only infrastructure involved, and to give the reason for Redis first.
- Moved the `userId` must-not-contain-`|` constraint into the terms list, and added `appliedRev` there.
- Named the five Lua scripts (join, cursor, heartbeat, leave, sweep) in one place before the rules use them, and merged the scattered script and subscription notes into one Mechanics list.
- Removed the repeated 'existing paths unchanged' bullets, leaving one line that says what is replaced and what is unchanged.
- Added snapshot seq to the client-state row of the table.
- Defined the first and last flags inline where they are introduced.
- Stated in the failover rule that the re-run join publishes no join event.
- Changed 'refresh' to 'renew' for the expiry in prose and diagram notes, so 'refresh' is not used for two meanings.
- Tightened wording throughout without changing the design, the numbers or the diagram flow.
- Defined 'node' and 'client' in the terms list, and explained that Lua scripts are atomic inside Redis so event order matches state order.
- Rewrote the summary opening to say 'WebSocket connection' and 'pushes that expiry forward' instead of 'renews', which is clearer for readers new to the stack.
- Added the reason for subscribing before join ('so no event can fall between the snapshot and the live feed') to the join rule.
- Left the diagram, tables and requirements unchanged, since they were already accurate and consistent.

### Holes
- None.
