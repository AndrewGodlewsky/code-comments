## Review of feat-02 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short 'Terms used in this document' section defining gateway, API key, Key Service, Redis, Lua script, fixed window and fail open, for readers who do not know the stack.
- Added a 'Reading the diagram' list after the sequence diagram that states the key rules in plain words (auth first, check before forwarding, counted at check time, fail-open behavior, Enterprise open).
- Explained what EVAL, TIME and the TTL do, and what the script's Redis clock versus gateway clock mismatch means in practice.
- Expanded the fixed-window tradeoff with a concrete example of the roughly 2x burst at a minute boundary.
- Clarified why the design uses one shared Redis and why per-instance and Key Service counting were rejected, and what the replica is for.
- Clarified the fail-open decision: no retry, the 50 ms deadline covers the whole call, and the stored count stays correct if the increment landed before the timeout.
- Reworded the Enterprise open decision so the options are numbered and say what each one means for the 'no guessed number' rule.
- Added a space around the cross-arrow in the diagram (R --x GW) so it parses reliably. The diagram's flow and content are otherwise unchanged.
- Added a plain-language intro to the terms list: API gateway, customer, Redis primary and replica, TTL, Retry-After, and the meaning of 401 and 429.
- Defined the Customer term explicitly, since the per-customer versus per-key distinction is central to the design.
- Explained why the Key Service was rejected for counting (it would take on request traffic), and why per-instance memory counting was rejected.
- Added a caveat that Redis replication is asynchronous, so a failover can lose the most recent increments, and that this design accepts that.
- Rewrote the fail-open note about a timeout after the increment, to explain that the request is forwarded, so counting it matches what happened.
- Clarified the Retry-After note: the script uses only the seconds part of TIME.
- Spelled out that Redis Lua scripts run atomically and that the Lua script is sent with EVAL, in the reading notes and terms.
- Kept the diagram, the Lua script, the requirements mapping, and the open decisions unchanged in substance; only wording around them changed.
- Defined the terms 'load balancer', 'primary/replica', 'sliding window', and 'fail open' in plain words, and explained what the `EVAL` command does.
- Rewrote the opening paragraph to say in one sentence what the gateway checks, when, and where the counts live, so a reader who does not know the project can follow it.
- Changed the diagram's Redis message label from 'EVAL check-and-increment' to 'Run check-and-increment script' so the step reads without the command name, and kept the key, limit, window and deadline values.
- Reworded the 'uses no budget' and fail-open explanations to be shorter and more direct, and made clear that the timeout case still counts the request, which keeps the stored count correct.
- Stated the Redis asynchronous-replication risk as a risk the design accepts, rather than only as a note that it happens.
- Added the definition of a sliding window as the upgrade path so the window-boundary tradeoff is easier to understand.
- Left the diagram structure, the Lua script, the requirements mapping, and all open decisions unchanged in substance.

### Holes
- None.
