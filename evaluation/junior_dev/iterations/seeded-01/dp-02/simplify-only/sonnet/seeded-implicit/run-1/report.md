## Review of dp-02 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-sentence summary at the top and a short terms list (event_id, received_at, raw log, archive, first copy, closed day, claim), and removed codes and cross-references.
- Rewrote each of the six steps with the same four parts: what starts it, what it does, where it keeps data, what happens on failure.
- Merged the reject bucket into the collector step: rejects are only listed in the response and counted, not stored. This is a decision that simplifies the plan; they are not accepted events, so the 90-day rule does not apply.
- Replaced several possible dedup and recovery mechanisms with one: a KV claim that records the first copy's log position, which also makes reprocessing safe. Crash duplicates are repaired by replay and listed as an open question rather than adding a new mechanism.
- Made the log partitioned by event_id and defined the first copy (earliest received_at, then log position), so live and replay agree.
- Specified that replay reads only the archive, including 8 days of look-back, so it leaves live dedup state untouched and handles old events arriving late.
- Replaced the vague monitoring item with a concrete alert list and moved failure handling into one table.
- Separated how the system runs from how to build it, and moved all unresolved items to a closing Open questions section: bot traffic, crash duplicates, warehouse append support, and live lag at day close.

### Holes
- None.
