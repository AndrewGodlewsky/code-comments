## Review of feat-02 (junior-v7, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote the file as a summary, terms, rules, diagram, notes and open questions, replacing the decisions table so each fact appears once. Every requirement and number from the first version is kept.
- Added the existing-system summary: gateway, Key Service, backend, and why Redis.
- Stated that the 5-minute cache holds the customerId and plan together (Q3).
- Spelled out the script: Redis TIME, windowStart, expiry set when the count first reaches 1, and Retry-After (Q2, Q6).
- Stated that Enterprise requests are forwarded, not counted and have no headers while the limit is open (Q1).
- Added a 100th and 101st request example (Q5).
- Added backend timeout handling: still counted, error behavior unchanged (Q4).
- Added late-Redis-answer handling: the answer is ignored and the count is not rolled back (Q7).
- Added the Key Service cache-miss failure behavior to Open questions (Q3).
- Merged the Terms bullets so the cache definition now says it is keyed by API key and holds both customer ID and plan (from Q3).
- Added to the Window term that the gateway never computes the window itself (from Q6).
- Folded Q2 details into the script rule: a missing key counts as 0, EXPIRE 120 is set when the new count is 1, and 120 s outlives the 60 s window.
- Reworded the backend-failure note to say the client gets the gateway's existing error for a timeout or unreachable backend (from Q4).
- Kept the 100th/101st example in Notes (from Q5) and the late-answer overcount in the fail-open note (from Q7).
- Added an open question that the exact status for a backend timeout or unreachable backend is existing behavior and unchecked.
- Kept all stated facts (6 instances, 100/min, Enterprise TBD, 50 ms, 429 and Retry-After, headers, 401 before Redis, metric name, 2x boundary trade-off). Removed nothing. Per Q1, the Enterprise skip rule is stated once in Rules. The diagram is unchanged.

### Holes
- Q3: Where does the gateway get the plan from, and what is cached for 5 minutes: the key-to-customer mapping, the plan, or both? What happens on a cache miss when the Key Service is slow or down? (author: The cache is keyed by API key and holds the single Key Service answer, customerId plus plan, for 5 minutes. The brief does not say what happens on a cache miss when the Key Service is slow or down. That is existing gateway behavior I have not verified, so it is listed under Open questions.)
