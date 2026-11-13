## Review of dp-02 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short "Terms used in this plan" section defining the log, consumer groups, acks, idempotent producer, key-value TTL, watermark, manifest and shadow table, for readers who do not know the stack.
- Split the document into "Part A: Live path" and "Part B: Replay one closed day" with a one-paragraph purpose statement for each, and stated up front that replay never touches live deduplication state.
- Labeled the replay steps R1 to R9 so the references in the failure cases (R2, R4.1) point at visible labels. The previous numbering reused 1 to 9 for both parts, which was ambiguous.
- Step 9.2 now says the MERGE goes to the partition for the received day of the copy being written, not "the day partition of the first copy". The old wording conflicted with the late-copy failure case, which writes a late copy to its own day. The behavior itself is unchanged.
- Rewrote the long sentences in each step into shorter ones, and spelled out what acks = all, idempotent producer, watermark and manifest mean where they first appear.
- Rewrote R8 so the replay window is stated directly (up to 90 days after D) instead of the earlier wording, which was hard to parse.
- Rewrote the late-copy failure case to name the affected day explicitly and say when it can be replayed.
- Kept all decisions, numbers and open items as they were. Open items 1 to 6 remain undecided and are unchanged in substance.
- Added a one-line 'pieces' overview after the goal so a reader sees the live path, archive, dedup and replay at a glance.
- Defined 'closed day' in the terms list, since the replay rules depend on it.
- Rewrote the malformed-event check as a three-item list, with a note that malformed events are not stored.
- Reworded the archive step: objects are created after the records' received_at, so each record lives at least its full 90 days. The old wording was unclear.
- Moved the 'copies arriving more than 7 days after first copy' check into the monitoring step, where it belongs, and kept it in the failure-case section.
- Added a plain-language explanation of why replay reads the ledger rather than the archive to pick first copies.
- Noted that the bot-classification slot stays empty until open item 1 is decided, so readers do not assume a design choice has been made.
- Simplified the latency budget into a list and clarified the 'copies per consumer' and 'get-then-set' assumptions.
- Stated that a replay reads only the archive and the ledger, to make its isolation from live state explicit.
- Changed 'A event' to 'An event' in the goal, and rewrote 'partly rebuilt' wording for plainness. Kept all numbering, names, TTLs, rules and open items unchanged; bot traffic remains open and undecided.
- Added a one-paragraph plain-language flow diagram after the goal, showing clients, collector, log, archiver, deduplicator and replay, so a reader sees the whole shape before the details.
- Defined 'log partition' versus 'warehouse day partition' explicitly, since both use the word 'partition' and the plan switches between them.
- Expanded 'replicated log', 'consumer group', 'acks = all', 'idempotent producer', 'TTL' and 'atomic partition replace' into plain explanations for a reader who does not know the stack.
- Fixed the grammar error 'A event' to 'An event' and tightened several sentences (for example the goal, the step 5 response, and the replay window) without changing their meaning.
- In step 7, replaced 'Drop it from events_clean' with 'Do not write it to events_clean' so it is clear that nothing is deleted from the table.
- In step 11, clarified that any copy arriving more than 7 days late means the client broke the retry contract.
- In the Part B intro and R2, stated the purpose of the ledger-based selection more plainly: the ledger lasts as long as the replay window, so every first-copy decision is still available.
- In R5, made clear that dashboards see the old partition until the swap and the new one afterward, with no partly rebuilt day.
- Kept all requirements, numbering, the Part A/Part B structure, failure cases, the six open items (including bot traffic left undecided) and the assumptions unchanged in substance.

### Holes
- None.
