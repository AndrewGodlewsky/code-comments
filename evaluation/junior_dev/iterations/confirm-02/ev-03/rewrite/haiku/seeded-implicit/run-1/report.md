## Review of ev-03 (rewrite, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three-sentence summary and a how-it-works-today sentence, which the first version lacked. Scope rules (one device, 200-member cap, sender excluded, out-of-scope items) were moved up so they are not lost.
- Added a terms section that defines outbox, msg_id, seq, presence TTL, Offline Inbox, at-least-once, idempotent and the other stack names the first version used without explanation.
- Replaced the four-line component map with a numbered ASCII diagram showing send (1-3), fan-out (4-6) and reconnect (7-8), as the brief asks.
- Merged the first version's terse bullets into eight numbered steps. Each step names its trigger, what it does and where its data lives. Repeated facts (heartbeat rate, 5 s timeout, 30-day expiry) are stated once, in the step where they apply.
- Decided: the 5-second no-ack rule applies to that one message only, because the brief says 'for that message'. The user stays online for later messages.
- Decided: any ack for a message removes that user's inbox entry, so an entry stays until the client confirms it. This makes an interrupted reconnect sync safe without a new mechanism.
- Decided: the Offline Inbox holds one entry per undelivered message with a reference to the message, and the text stays in the Message Store. The first version said only that the inbox 'tracks undelivered messages'.
- Decided: idempotent retries work by returning the existing seq when a msg_id already exists. This is the simplest way to meet 'a retry must never create a second copy'.
- Added a failure table covering every failure the brief names (store write, lost ack, gateway death, 5 s timeout, push failure, 30-day expiry) plus the outbox, relay and worker crash cases that the at-least-once design depends on.
- Added two open questions the brief leaves unanswered: how long the Message Store keeps text (needed for the 30-day promise), and how a long backlog is sent on reconnect.
- Net effect: the document is longer than the first version, about four to five times, because the brief requires the failure notes and every fixed requirement. No stated requirement, limit or number from the brief or the first version was dropped.

### Holes
- None.
