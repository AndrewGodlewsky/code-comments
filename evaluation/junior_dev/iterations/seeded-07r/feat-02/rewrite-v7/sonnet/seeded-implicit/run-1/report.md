## Review of feat-02 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-sentence summary and a short description of how the gateway works today (6 stateless instances, Key Service with 5 minute cache, forward to backend), placed before the diagram.
- Added a Terms section defining window, counter key, Lua script, TTL, Key Service, plan and fail open, and why the script prevents overshoot.
- Replaced the bare happy-path diagram with one showing the 401, 429, under-limit and fail-open branches, the 50 ms timeout, and the response headers.
- Merged the terse Notes bullets into numbered steps that say what triggers each step, what it does, and what happens on failure; removed the separate repeated notes.
- Made the unstated design decisions explicit: fixed one-minute window, counter key per customer, TTL of 120 s, rejected requests change nothing, Retry-After = seconds to end of window, fail-open responses omit the X-RateLimit headers.
- Added a failure table, a short Rollout section kept apart from the runtime description, and an Open questions section for the undecided Enterprise limit and the Redis topology.
- Kept every original fact: 100/min Standard, Enterprise TBD, per-customer sharing across keys, 401 touches no counter, 429 + Retry-After, backend failures still count, headers, 6 instances shared counts, 50 ms fail open with the ratelimit_store_unavailable metric.

### Holes
- None.
