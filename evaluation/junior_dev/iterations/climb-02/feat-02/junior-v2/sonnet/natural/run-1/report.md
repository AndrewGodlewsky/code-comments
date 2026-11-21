## Review of feat-02 (junior-v2, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Atomicity and diagram: the Lua script now takes customerId and limit and builds the key from Redis TIME, so the gateway no longer needs to know the time (Q1).
- Limits: added the explicit handling for an unset Enterprise limit. The request skips the check, is forwarded, is not counted, and gets no headers. Added a matching alt branch to the diagram and an open item (Q2).
- Atomicity step 3: said how the script detects the first increment (INCR returns 1) and set the 120 s expiry from that moment. Step 1 now treats a missing key as count 0 (Q7).
- Added a Header meaning line, defining X-RateLimit-Limit and X-RateLimit-Remaining (Q6).
- Fail open: stated that an increment made by a script that finished after the timeout is kept (Q5).
- Backend failures: stated that the gateway's existing backend error handling is unchanged (Q6).
- Diagram note: cache is separate on each gateway instance (Q4).
- Open questions: moved the Enterprise limit item here and added one line for the unverified existing behavior (Key Service down, unknown-key caching, unreachable backend) (Q3, Q4, Q6).
- Merged the Time source and Retry-After lines to shorten them, and removed the duplicate Open item note (the Open questions section replaces it).
- Removed the separate Time source bullet and merged it into Atomicity (Redis TIME builds the key and avoids clock skew).
- Merged the Header meaning bullet and the 429 headers note into one Headers bullet.
- Shortened the Atomicity step 3 wording and the Overshoot note; dropped the redundant 'first increment' repetition in the Window bullet.
- Shortened the Backend failures bullet to drop the repeated 'unchanged by this design' phrasing.
- Kept the diagram, requirements coverage and the open questions together at the end.

### Holes
- Q3: What does the Key Service return for an unknown key, and what happens if the Key Service itself is down or slow on a cache miss? (author: The brief does not say what the Key Service returns for an unknown key beyond 'unknown', which gets 401. It also does not say what happens if the Key Service is down or slow. That is existing gateway behavior this design does not change. I listed it under Open questions.)
- Q4: Is an unknown key cached too, or only valid ones? And is the 5-minute cache per gateway instance? (author: The cache is in memory on each gateway instance, since the instances are stateless and separate (from the brief), and I added 'separately on each instance' to the diagram note. Whether unknown keys are cached is not stated in the brief, so I do not know. I listed it under Open questions.)
