## Review of ev-01 (rewrite, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a summary of how checkout works today and what the new flow changes, in three sentences before the terms.
- Added a terms section that defines each name a newcomer would not know: outbox, relay, broker and topic, event, key by orderId, consumer group, at-least-once, processed_events, reservation, idempotency key, conditional update and DLQ.
- Kept the Mermaid sequenceDiagram unchanged, placed directly after the terms, covering the happy path and both cancellation paths.
- Merged the old 'Design decisions' and 'Notes on the flow' into seven numbered steps. Each step gives its trigger, what it writes, which part keeps the data, and each rule appears once.
- Removed the separate 'Design decisions' section. Its rules (outbox ownership, Payment's CHARGING commit, the conditional status update, the email trigger, and the ordering guarantee) now sit in the steps that apply them.
- Kept the 'Where state is written' table unchanged, because the brief requires it.
- Kept the 'Duplicates' section and cut it to four bullets, one per duplicate case, with no repeated rules.
- Moved all failure handling into one table. Removed the failure bullets that repeated the retry wording in the steps.
- Kept every number, status, topic name, interval (500 ms, 1 s, 10 s, 60 s), rule and the open question from the first version. Added the 'does nothing more' note on a conditional update that matches no row, which the diagram and duplicates section already implied.
- No junior questions or answers were shown, so this rewrite used none. The rewrite is based on the first version and the brief.

### Holes
- None.
