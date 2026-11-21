## Review of feat-02 (junior-v4, author sonnet, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote the diagram to show return arrows, the 401 branch, the 429 branch, the allowed path and the fail-open path.
- Added a short intro, how the gateway works today, and three defined terms.
- Specified the Redis key, the limit passed in by the gateway, the script's return value and no increment when rejected.
- Specified Retry-After (seconds to minute end), a 120 s key expiry, and which responses carry which headers.
- Stated the 50 ms is a Redis call timeout and accepted the fixed-window boundary burst.
- Added Open questions for the Enterprise limit, metric ownership and Key Service failure.
- Merged the three notes on the script (returns allowed/rejected, does not increment when at limit, gateway decides) into one bullet; dropped 'the gateway makes the 429 decision', which the diagram already shows.
- Merged the 'steps run in order' and 'sends customer ID and limit' notes into one bullet and cut the redundant ordering note.
- Merged the Redis key format, plan-to-limit mapping, and 120 s expiry notes; removed the repeated plan-to-limit mapping sentence.
- Merged the Retry-After and 429-headers notes into one bullet.
- Moved the 2x boundary burst note to the end of the notes as its own bullet and split it from the 429 header note.
- Shortened term 'Customer budget' to 'Budget' and added 'behind a load balancer' to the existing-system summary.

### Holes
- Q8: What happens to Enterprise customers today, given the limit is TBD? And what happens if KeyService itself is down or slow? (author: Enterprise limit is not decided by Product and I have no defensible interim behavior, so it is listed under Open questions rather than guessed. Key Service failure is existing behavior and unchanged; I have not verified what it does today, so it is noted as out of scope.)
