## Review of feat-02 (junior-v6, author haiku, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Changed: Rewrote the short notes into a summary, a terms list, the diagram, numbered steps, counter rules, a failure table and open questions, so a newcomer can follow the flow without asking. Kept the diagram form with summary and terms before it and notes after it.
- Changed: Stated that the existing system works today (Key Service lookup, 5-minute cache, forward) before describing the change.
- Changed: Added that the Key Service call comes before Redis, because the counter key needs the customer ID.
- Changed: Added that a 401 never touches Redis and that a rejected request is not counted, to keep requirements 3 and 4 explicit in the flow.
- Changed: Added the counter key, TTL, window reset, Retry-After rule and fixed-window tradeoff, all decided here, since the first version left them out.
- Changed: Added that a backend 500 still counts, and that passing responses carry the X-RateLimit headers.
- Changed: Added the Lua script's atomicity and the shared counters so the 6x overshoot requirement is visible in the flow.
- Changed: Added the 50 ms timeout and fail-open rules, with no headers and no retry, as the simplest handling the brief allows.
- Changed: Kept the Enterprise limit visibly open, with its own open question, and kept the Key Service failure and alerting gaps as open questions rather than inventing behavior.
- Changed: Kept every stated fact from the brief and the first version: per-customer budget shared across keys, 100/min Standard, 401, 429 with Retry-After, the 50 ms fail-open rule, the ratelimit_store_unavailable metric, and the X-RateLimit headers.
- Enterprise: replaced the unstated 'Enterprise requests have no limit' with 'step 3 is not defined for Enterprise; the limit is open' in step 3, Enterprise counter rule and open questions, because the old wording silently left Enterprise customers unlimited (Q9).
- Diagram: added a note in the key-resolved branch that the Enterprise limit is open, so the gap is visible in the diagram (Q9).
- Failure table: added a row for Enterprise requests marking the outcome as not defined (Q9).
- Step 2: added that a plan change takes up to 5 minutes to apply, until the cached answer expires (Q10).
- Step 3: said the same script sets the TTL when it creates the counter (Q13).
- Step 5: defined X-RateLimit-Remaining as the limit minus the new count returned by the script, never below 0, and said no reset header is sent in v1 (Q12).
- Step 6: said the count is not undone and one failed call can leave at most one extra count (Q11).
- Counter rules: TTL line now says it is set only at creation, not refreshed, and why the key lasts to the window end (Q13).
- Terms: added Limit, Lua script (atomic), TTL, Cache hit, Retry-After, so each term the questions touched is defined in one line.
- Structure: reordered into summary, terms, diagram, steps, counter rules, failure table and open questions. Plan intent unchanged; all first-version requirements and numbers kept.
- Step 3 and the Window term: the Lua script, not the gateway, works out the window from Redis server time and builds the counter key. The gateway passes only the customer ID and the plan's limit. This corrects the earlier answer that the gateway passes the window (Q14).
- Main flow diagram: the check_and_incr call now shows customer ID and limit, with a note that the script sets the window from Redis time (Q14).
- Step 2: added that each gateway instance keeps its own in-memory cache, so instances can disagree on the plan for up to 5 minutes after a plan change (Q15).
- Step 6: added that every request tries Redis afresh with no memory of earlier failures, so each request waits up to 50 ms during an outage (Q16).
- Step 4: stated that a 429 response carries no X-RateLimit headers, as the earlier answers said.
- Added a Fixed window term so the window shape is defined before it is used.
- Counter rules: moved the key, TTL, Retry-After and window-shape rules into one section after the steps. Dropped the separate Enterprise rule, since step 3 and the open questions already cover it.
- Open questions: added the timeout scope, meaning whether the 50 ms includes connecting to Redis (Q16).
- Reordered the sections to summary, terms, diagram, steps, counter rules, failures, open questions. Kept every requirement and number from the brief and the first version.
- Rewrote the whole file in the newcomer order: summary, terms, diagram, numbered steps, counter rules, failure table, open questions. No requirement, limit or rule from the brief or the first version was dropped.
- Step 3: spelled out what the script does, including that a missing counter counts as 0 and the first allowed request creates it at 1 (Q17).
- Step 3: the script keeps no limit and compares the count with the limit the gateway sends (Q19).
- Step 2: each instance applies the limit from its own cached plan, so a plan change can leave a downgraded customer past the new limit for up to 5 minutes (Q19).
- Step 5: X-RateLimit-Remaining is derived from the count only (Q18).
- Allowed reply from check_and_incr now carries only the new count; the seconds field is returned only for not-allowed (Q18).
- Step 6: defined what counts as a failure (error reply, dropped connection, unexpected reply, no answer in 50 ms) and that the 50 ms starts when the gateway sends the call (Q20).
- Terms: Customer ID states that all of a customer's keys use one counter (Q21). Counter defined as 0 when missing (Q17).
- Diagram: the 401 branch states Redis is not touched, and the failure branch names all Redis failure forms (Q20).
- Added a summary paragraph that says how the system works today (key lookup, cache, forward) and why the design is shaped this way (shared Redis counter, atomic script, fail open). Kept the brief's public REST API and six-instance wording and the 'not 6x the limit' requirement.
- Moved the terms before the diagram and the steps and notes after it, per the diagram layout rule. Added terms for Redis, Key Service, backend, Lua script, atomic, cache hit and cache miss. Defined the Key Service and backend, which the first version used without explanation.
- Removed semicolons inside Mermaid Note lines, because Mermaid treats a semicolon as a statement separator. The Enterprise note now reads 'limit comes from the plan, Enterprise limit is open'.
- Step 2: stated that each instance keeps its own cache, that a plan change lags by up to 5 minutes, and that a downgraded customer can exceed the new limit for that time. Added a pointer to the Key Service failure open question. Removed the repeated cache wording.
- Step 3: stated that the gateway sends no window and that the script works out the window from Redis server time. Stated that the first allowed request sets the TTL in the same step. Merged the repeated Enterprise wording into one sentence that points to Open questions.
- Step 5: stated that the gateway reads only the new count from an allowed reply, that Remaining is never below 0, and that no reset header is sent in v1.
- Step 6: defined the failure path precisely (any reply other than the two shapes counts as a failure, the 50 ms is measured from when the call starts, all failures take the same path). Stated that no circuit breaker or failure memory exists, so each request waits up to 50 ms during an outage. Kept the accepted one-extra-count risk.
- Merged the fixed-window and Retry-After facts into a Counter rules section. Kept the 60-second TTL, Retry-After as at least 1 second and sent only with 429, and the 200-request boundary example.
- Kept the failure table and all four open questions unchanged in substance. Removed no requirement, limit, number, setting or rule from the first version or the brief: 401 with no counter change, 429 with Retry-After and no forward, 429 not using budget, backend 500 still counted, the 50 ms fail-open path with the ratelimit_store_unavailable metric, Standard 100 per minute, Enterprise open, and the X-RateLimit headers.

### Holes
- Q4: How is the limit for a given customer found? Where does 'Standard' vs 'Enterprise' come from, and what happens to Enterprise customers while the limit is TBD? (author: The lookup is checked: the plan comes from the Key Service through the 5-minute cache, and Standard maps to 100 per minute. Product has not decided the Enterprise limit, so this design does not set one and cannot yet say what an Enterprise request is limited to. It is left as an open question in the file.)
- Q9: The Standard limit is 100 per minute, but what do the Enterprise requests do in step 3 today? Does the gateway skip check_and_incr, or call it with some value? (author: The brief gives no Enterprise limit, so the design does not say what step 3 does for Enterprise requests. Skipping the check and calling the script with a placeholder limit are both choices the brief does not make, so I did not pick one. The earlier wording, that Enterprise requests have no limit, was an unstated decision and is removed. It is now an open question.)
- Q16: Does the 50 ms timeout cover the whole Redis call, including connecting? And does a Redis failure on one request affect the next request, or is every request tried fresh? (author: The brief does not say whether the 50 ms covers connecting to Redis or only the command. I did not guess, and it is now an open question. Decided: each request tries Redis afresh. The design has no circuit breaker and remembers no failure between requests, because a breaker is a new mechanism the brief does not require. So during a Redis outage each request waits up to 50 ms before it is forwarded. Step 6 says this.)
