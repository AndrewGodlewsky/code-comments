## Review of ev-01 (junior, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Reordered the document into summary, terms, diagram, steps, design choices, state table, failure table and open questions, so each fact appears in one place.
- Added terms for outbox, relay, broker, topic, consumer group, eventId, at-least-once, processed_events, idempotency key and DLQ (Q1, Q2, Q9).
- Step 3 now says Inventory checks its stock count before reserving. Where that count is stored is open question 8 (Q3).
- Changed the timeout retries in the diagram and step 5 from broker redelivery to an in-place retry by the Payment consumer, matching the open question about the paused partition (Q5).
- Added a Payment crash path to the diagram: redelivery, ATTEMPTING marker, same-key card call, then CHARGED and PaymentCharged (Q6).
- Stated that the consumer moves the message to the DLQ, pages on-call and acks the original. The human re-drive or cancel procedure is left as open question 1 (Q7).
- Stated that the processed_events insert rolls back with the state change, and that the card and email calls sit outside that transaction (Q8).
- Stated that the writing service creates the eventId in the same transaction as the outbox row (Q9).
- Added open questions for the customer's view of the outcome (Q4), the stock store (Q3) and the broker product (Q1).
- Made the email failure rule explicit: the send is recorded and does not throw, so it never enters the retry path. The recommendation is kept and still needs confirmation (open question 7).
- Merged repeated rules (the card key, the dedupe rule, the ATTEMPTING meaning) so each is stated once, and moved the first version's per-step failure notes into one failure table.
- Kept every fact from the brief and the first version, including the six consequences, which are now open questions 1 to 6 and the failure table.
- Payment's ATTEMPTING commit no longer writes processed_events. The processed_events row is written only with the final CHARGED or DECLINED transaction. The earlier text would have made a crash-redelivery and the in-place card retries hit the duplicate check and skip the card call (Q10, Q11).
- Step 5 now lists Payment's checks in order: processed_events, then the payments row, then the ATTEMPTING insert, the card call and the final transaction (Q10, Q12).
- The 'No second charge' bullet now says Payment writes nothing on a redelivery after CHARGED or DECLINED, and that the relay re-publishes the existing outbox row (Q12).
- The brief says every consumer retries after 1 s, 10 s and 60 s when its handler throws. The earlier text applied this only to Payment. The Retries bullet and the failure table now cover every consumer (found while answering Q11).
- Added a 'Separate consumer groups' bullet, and failure rows for an Inventory DLQ and an Order Service DLQ on PaymentDeclined. The Payment DLQ row now says it affects only Payment's group (Q13).
- Added open question 11 about a reservation left RESERVED on a CANCELLED order (Q13).
- The Duplicates bullet now names Payment's exception to the same-transaction rule. The diagram's Payment notes were changed to match: the ATTEMPTING commit has no processed_events row, and the crash-redelivery note says so.
- Step 8 now says the release runs in parallel with step 7. The earlier text did not say so.
- The 'Where each piece of state is written' table now says processed_events is written with each consumer's final state change.
- Rewrote the whole document once for a newcomer, using the first version's facts and the junior's 13 answered questions. The main flow, failure cases and open questions are all kept.
- Summary: cut to three sentences that say how checkout works today, what changes, and the core rule (stock before charge, Order Service sets final status).
- Terms: added the terms a newcomer needs and the junior asked about: partition, ack, guarded update, event (eventId, orderId, type, and who creates the eventId), card provider and email provider. Removed the duplicate definition of the relay's behaviour.
- Added a Rules section after the diagram that collects the business rules from the brief once, so they are not repeated in the steps or design choices.
- Steps: each now names its trigger, what it does, and what data it keeps, and no longer retells the diagram sequence. Step 5's checks are ordered explicitly, with the ATTEMPTING commit writing no processed_events row, as the junior's Q10 and Q11 required.
- Merged the duplicated failure text from the steps into one failure table. Added to it the in-place retry's partition blocking (Q5), the broker-down customer impact, and the rule that a DLQ'd consumer acks the original and moves on.
- Design choices: kept each decision once. Added that each consumer reads every event and skips unknown types (Q2), that the relay alone re-publishes an unsent row after CHARGED or DECLINED (Q12), and that the retry runs in consumer code (Q5).
- Failure table: added an Order Service DLQ row for StockRejected, which the first version missed because Order Service also consumes it. This is a correction, not a change of design.
- Added a short Build and rollout section stating that no rollout plan is in the brief. Open questions 1-11 are kept, worded plainly, with no internal codes.

### Holes
- Q3: How does Inventory decide there is enough stock, and where is the stock count stored? The state table only lists reservations. (author: The brief does not say where Inventory keeps its stock count or how it checks it. The design only covers the reservations table. The rule (reserve only when stock is enough, otherwise reject with no charge) is fixed by the brief, but the store and the check are not known. Added as open question 8 and named in step 3.)
- Q4: After the 202 Accepted, how does the customer find out whether the order was confirmed or cancelled? (author: The brief gives no status endpoint and no push to the customer after the 202. The only customer notice it states is the confirmation or cancellation email, which is sent after Order Service has set the final status. Whether the customer can query order status is not known. Added as open question 9.)
