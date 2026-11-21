## Review of rt-01 (rewrite, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the document in the skill's order: summary with how presence works today, terms, diagram, steps, failure table, rollout, open questions.
- Added the missing mechanisms: Redis keys and channel (presence:{docId} sorted set with expiry scores, cursors:{docId} hash, pres:{docId} channel), the atomic register, refresh and sweep scripts, and exact TTLs (30 s entry, 10 s refresh, 5 s sweep, 60 s key expiry) with the crash timing worked out against the 45 s limit.
- Added how a joiner sees everyone's caret immediately: the snapshot returns live entries plus the stored cursors, and subscribing before reading closes the race.
- Merged the one-line notes (throttle, transformPosition, dedupe tabs, seq numbers, TTL, edits unchanged) into the steps where they apply. Specified the receiver rules: ignore own userId, seq per connId, hold future revs, transform, drop on HistoryGone, re-transform on each applied revision.
- Redrew the diagram: Alice and Bob on different nodes, Bob already present, all requirements shown (join with snapshot, cursor with 50 ms drop, heartbeat plus sweep loop, clean leave, node crash). The crash was moved to Alice's node, so a surviving node sweeps.
- Added failure table, including pub/sub reconnect resnapshot and Redis failover re-registration, plus a short rollout section separate from the runtime flow. Retiring Postgres polling, the table and nightly job is a decision, not a brief requirement.
- Added open questions: avatar and name source, unacknowledged local ops in cursor position, unmeasured Redis load, and the 60 ms jitter margin.
- Cut the vague framing sentence ('Heartbeats keep things fresh, and a sweeper cleans up') and the standalone note list; nothing stated in the first version or the brief was dropped. The file is longer than 1.5x the first version because the first version left most mechanisms unstated.

### Holes
- None.
