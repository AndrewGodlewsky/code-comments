## Review of ev-03 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the whole document once for a newcomer, in the order: summary, terms, diagram, steps, failure table, open questions. No junior questions were supplied, so no answers were applied.
- Restored a fact the first version dropped: the out-of-scope list (typing indicators, read receipts, edits, deletes).
- Restored a fact the first version dropped: history retention is outside this design.
- Restored the one-device-per-user assumption, now in the presence store term and the overwrite rule.
- Replaced the 'Where state lives' section by putting each store's fields into the terms list, once, so each fact appears in one place.
- Defined plain-language terms a newcomer would not know: Message Store, seq, message_id, row lock, gateway node, WebSocket, frame, heartbeat, presence store, fanout outbox, relay, fan-out worker, mailbox, TTL, push, ack, client state, at-least-once, CDC.
- Turned the diagram's numbered steps into a step list that adds trigger, data owner and failure handling, and removed repeated diagram text from the prose.
- Moved failures that touch one step to a single 'If it fails' line under that step, and kept multi-part failures (gateway death, presence outage, ack timeout, TTL expiry, membership change) in one table.
- Merged the 'Ordering and limits' section into the steps: seq order per socket in 8a, concurrent 5-second timers in 8a, replay order in 13, overlap handling in 14, live gap handling in 17, and the 199-recipient bound in 5.
- Merged the 'Open decisions' section into the open questions, and kept the push-on-ack-timeout trade-off there.
- Added one open question not in the first version: the brief does not say how connections authenticate or what happens when auth fails. This is a gap, not a decision, so it is listed rather than invented.
- Kept the diagram verbatim, since its step numbers 1 to 17 match the steps, and kept every fixed requirement, limit, number and failure rule from the brief and the first version.

### Holes
- None.
