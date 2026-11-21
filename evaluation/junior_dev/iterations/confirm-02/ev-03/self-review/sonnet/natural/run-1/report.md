## Review of ev-03 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a one-paragraph summary and a component glossary at the top so a reader new to the stack knows what each box is.
- Defined terms (outbox, relay, nudge, presence) where first used instead of assuming them.
- Redrew the diagram with clearer labels, consistent step numbers (1-11, a/b branches), and explicit 'ONE transaction' and 'only after 9b succeeds' markers.
- Replaced the cramped reconnect section of the diagram with a small picture plus a numbered list R1-R7, and stated that presence is registered before the inbox is read.
- Fixed step numbering inconsistencies (old R6/R7/R8 mix; 'go to 9b' ambiguity) so the reconnect steps match the failure table's reference to R7.
- Reworded 'Process dies after commit' to 'Any process dies after commit' and clarified the guarantee.
- Spelled out the reconnect race as a sequence and why the entry would otherwise sit unseen.
- Clarified in the Recipients rule that recipients are processed concurrently, merging it with the old online-delivery sentence about not blocking.
- Added a Terms section defining msg_id, seq and the two senses of ack, so a reader new to the project can follow.
- Renumbered the diagram steps to a clean sequence (send 1-3, fan-out 4-10a, offline 8b-9b) and updated every step reference in the text to match.
- Fixed the diagram: the transaction note is now one clear label on step 2, and the presence-registry details moved out of the worker box into the component list.
- Made explicit that the member list is fetched once per message and presence is checked per recipient.
- Clarified the ack outcome at the bottom of the diagram (ack within 5s: done; no ack: do 8b).
- Added a Why the outbox rule explaining the crash problem the outbox solves.
- Moved the presence TTL and heartbeat details into the Presence Registry component description.
- Replaced ambiguous queue 'acknowledge' wording with 'mark done' so it is not confused with client acks.
- Stated in the Send rule that a failed write gives the sender an error and delivers nothing.
- Tightened the Assumptions wording on atomic commit.
- Defined 'offline path' as a term and clarified the two meanings of ack (sender vs recipient) up front.
- Moved the heartbeat and 30-second offline rule into the Gateway and Presence Registry component entries so each component is self-explanatory.
- Added that a queue job is removed only when a worker marks it done, which the failure table relies on.
- Clarified in the diagram that the step 10a client ack travels back through gateway B to the worker.
- Clarified that R7 repeats R3-R6.
- Rewrote the 'Why the outbox' rule to say what the gateway would otherwise do, and used 'acknowledged' consistently for sender-side acks.
- Rewrote the reconnect race row as an explicit sequence so the order of events is easier to follow.

### Holes
- None.
