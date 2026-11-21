## Review of rt-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a "Background terms" section defining gateway node, connection, revision, lease, heartbeat, TTL, pub/sub, hint, seq and transformPosition (including HistoryGone and the 500-revision history limit), so a reader outside the project can follow the design.
- Added a "How it works" introduction and a plain-language walk-through of the five diagram steps (join, cursor move, heartbeat, clean leave, crash), explaining why each step happens and what each node does. The diagram itself is unchanged.
- Rewrote the state table in plainer wording, with each Redis key described in words before its name, and clarified what the sorted-set score means.
- Clarified the crash timing arithmetic: the lease deadline is last heartbeat plus 30 s, and the last heartbeat is at most 10 s before the crash, so the deadline is at most 30 s after it. Stated the 40 s worst case explicitly.
- Added a stall bullet to the timing budgets, explaining the ZADD return value of 1 (re-add and rejoin) that was previously only in the notes.
- Reorganised the client rules into seq ordering, held carets, transform and presence-list rules, and stated the never-draw-ahead-of-applied-revision rule first in plain terms.
- Added a sentence that each heartbeat rewrites the identity fields as well as resetting the TTL. This is a new rule, not in the original: the original heartbeat only refreshed the TTL, so an identity hash that expired during a stall would have come back incomplete. Please confirm this is the intended behaviour.
- Clarified that the first cursor is sent right after open, so idle users still have a caret for joiners, and that join reads state from Redis rather than from pub/sub history.
- Removed no requirements. Kept the intent, the fixed requirements' numbers (50 ms, 2 s, 45 s, 10 s heartbeat, 30 s TTL, 60 s sorted-set TTL) and the diagram.
- Rewrote the opening and the background terms in plainer language. Each term now has one short line, and terms such as lease, hint and pub/sub explain what they do rather than only what they are.
- Added a short 'How it works in brief' section with three plain statements: Redis holds the state, pub/sub only says re-read, and every key has a TTL.
- Shortened the step-by-step notes and made each one say what happens and why it is safe.
- Simplified the state table: column names now say what each column means, and cells are shorter.
- Added a rule that a snapshot skips a member whose identity hash has already expired. The identity hash and the lease run out at about the same time, so the gap was real and unstated.
- Explained that reads skip members whose lease has passed, but clients change only when a hint arrives, so the list changes at the sweep.
- Added an 'Open gap' section. The seq counter lives in the caret hash, so if that hash is lost, seq restarts at 1 and receivers drop new carets until seq passes the old value. The design does not fix this, so the section lists the options for the owner to decide.
- Mermaid diagram: the message logic is unchanged. Wording of the step-1 and crash notes was tightened, and the crash notes now point to the sweep.
- Added a plain-language glossary of the Redis parts (sorted set, hash, TTL, pub/sub) and the commands used (ZADD, ZREM, ZRANGEBYSCORE, HSET, HINCRBY, PEXPIRE, PUBLISH, SUBSCRIBE and others), with the meaning of their return values where the design relies on them (ZADD returns 1 or 0).
- Explained gateway nodes, WebSockets and the load balancer, and why shared state must live in Redis, in the background section.
- Defined lease, heartbeat, hint, revision and transformPosition in full sentences, and explained why a caret is only meaningful at a revision.
- Rewrote the step descriptions as plain sentences. Each step now says who acts, what is written, and what is published.
- Explained the crash timing arithmetic: the last heartbeat sets the deadline 30 s after itself, so the deadline is at most 30 s after the crash, and the sweep adds at most 10 s, for 40 s total.
- Explained that only the node whose ZREM returns 1 publishes the leave hint, so exactly one announcement goes out.
- Clarified the stall case: a late heartbeat's ZADD returns 1 because the member is new again, which triggers a fresh join hint.
- Clarified the transform rule: after each applied batch, the caret is moved to appliedRev and stored with that new revision, so the original revision is no longer needed.
- Clarified that held carets are kept per user (highest seq only), and defined appliedRev where it is first used.
- Spelled out the two ways the seq-loss gap can occur, and marked the decision as needed.
- Kept the Mermaid sequenceDiagram unchanged, so its structure, messages and timings are the same as before. Kept the five-step scope and the section order.

### Holes
- None.
