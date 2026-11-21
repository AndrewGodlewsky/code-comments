## Review of ev-01 (junior, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a summary of today's behaviour and the new flow, and a terms list (broker, topic, partition, consumer group, outbox, relay, processed_events, idempotency key, DLQ).
- Added an events table naming each event, its publisher and its consumers, so the flow of data is visible before the diagram.
- Rewrote the Mermaid diagram: the first version showed only the happy path plus a one-line note. It now has alt branches for card approved, card declined and not enough stock, with the outbox writes and the relay shown as notes.
- Named the card decline and stock shortage paths in the diagram so both cancellation paths are visible. Notification now sends a cancellation email on both paths, as the brief requires. The first version sent email only on confirmation.
- Stated who releases the reservation on decline (Inventory, on PaymentDeclined), which the first version left out.
- Set the card idempotency key to the order ID, so a retry or a re-published event cannot charge twice.
- Replaced 'usual retries and a DLQ' with the brief's rule: four attempts at 0 s, 1 s, 10 s and 60 s, in-place retries, DLQ, paging and no undo.
- Added the duplicate rule (processed_events, written in the same transaction as the effects) once, in shared rules, so the steps do not repeat it.
- Added a table of which database holds which state and which events each service sends.
- Set the rule that Order changes status only from PENDING, and that Order is the only service that changes status.
- Removed the 'Parts' line; its facts are now in the summary and the events table.
- Added open questions for the DLQ replay and stuck stock, the status read endpoint, the partition-wide wait during retries, and whether email failures should page on-call.
- Step 2: added that a crash after the broker ack but before the mark re-publishes the row, and consumers skip it by eventId (answers Q14).
- Step 4: added that the retry reuses the same key and message, that nothing is published until the result is saved, and that a repeat call returns the same decline (answers Q10, Q11).
- Step 5: added that a release with no reservation does nothing and that a release always follows its reservation on the same partition (answers Q15).
- Step 6: added that a non-PENDING order changes nothing and writes no event, and why this should not happen in the normal flow (answers Q9).
- Step 7: added that a crash after sending can cause a duplicate email (answers Q13).
- Shared rules, Duplicates: added that eventId is saved only on success, so a DLQ message is not recorded and a DLQ replay handles it again (answers Q12).
- Open questions: added the Inventory DLQ on PaymentDeclined case, the Order DLQ on PaymentCaptured case, the stray-capture refund gap, the idempotency key retention gap, and the duplicate email window (answers Q9, Q10, Q13, Q16).
- Events table: added a column for the extra data each event carries, so Inventory gets items from OrderPlaced and Payment gets the amount and card reference from StockReserved (Q17, Q18).
- Terms: added the card reference, defined in one line.
- Step 1: the order write now includes its items, amount and card reference (Q17, Q18).
- Step 2: stated what happens during a long broker outage: rows wait, new orders still get 202, rows go out oldest first on return (Q21).
- Step 3: Inventory reads the items and copies the amount and card reference into StockReserved (Q17, Q18).
- Step 4: the card call runs before the database transaction, not inside it, with a reason; the retry rule is referenced in Shared rules rather than repeated (Q19).
- Shared rules, Duplicates: a consumer moves its topic position past a message only after handling it, skipping it as a duplicate, or sending it to the DLQ (Q20).
- Where state is written: Order's row now also holds items, amount and card reference.
- Open questions: added the unknown form of the card reference and how it is protected, and that the order fields are not defined in the brief (Q18). Added the unknown outbox wait limit and stuck-relay alert (Q21).
- Summary cut to three sentences. It keeps how checkout works today and why the flow is shaped this way. The brief's claim that a slow service 'delays only its own step' was reworded to 'no longer holds up the customer's request', because the in-place retries can delay other orders on the same partition (kept as an open question).
- Replaced the first version's 'Parts' list with a Terms section. Each term the newcomer needs is defined in one plain line: broker, event, partition, consumer group, position, ack, outbox, relay, idempotent, processed_events, card provider, card reference, idempotency key, DLQ and on-call. Everyday words such as transaction were left out.
- Moved the event table into Terms, next to the diagram, and added the note that each consumer ignores the types it does not handle.
- Kept the Mermaid diagram unchanged. It sits directly after the terms and its notes follow it in the steps.
- Steps rewritten so each has a trigger, what it does and which store holds its data. Each step now stands alone. Step 4 gives the reason the idempotency key is the order ID, and states that the card call runs before the database transaction.
- Step 6 now states that a non-PENDING order still records the eventId as handled, so repeats are skipped (from the round-2 answer).
- Step 5 now states that a release with no reservation does nothing, and why a StockReserved cannot arrive after a release.
- Merged the card-provider rule into Terms and step 4, and removed the separate shared-rule copy. Kept the duplicate and retry rules in Shared rules. Added that a message that ends in the DLQ is not saved to processed_events, and that a consumer's position moves only after handling, skipping or dead-lettering.
- Failure handling collected into one table ('What happens when things fail'), covering the outbox, relay, consumer errors, Payment crashes, provider timeouts, non-PENDING orders, email failures and crashes before position moves. Steps no longer repeat failure text.
- Kept the 'Where state is written' table, because the brief requires it. The steps name their data only briefly.
- Open questions: all facts kept. The three DLQ cases were merged into one bullet with sub-items, and the 'confirm' questions were kept as they were. Removed the question codes, so no reference relies on labels such as Q7.
- Removed all round references and codes (R3, Q7 and similar) from the text, so the document stands alone for a newcomer.

### Holes
- None.
