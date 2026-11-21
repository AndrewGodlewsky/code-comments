## Review of feat-02 (junior-v7, author haiku, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a Terms section defining API key, Key Service, plan, customer ID, Redis, Lua script, fixed window, TTL and fail open (Q1, Q2, Q6).
- Rewrote the diagram with alt branches for 401, 429, the Enterprise path and fail open, so the key is resolved before the Redis check and 401 and 429 stop before the Backend (Q5, Q7, Q8).
- Added the counter key format rl:<customer ID>:<minute> and the minute taken from the Redis clock (Q2).
- Set the window to a fixed clock minute with a 60-second TTL set on first request (Q6).
- Added the rule that check_and_incr does not increment when denied, so 429 requests use no budget (Q4).
- Added the rule that the limit comes from the plan via gateway config and is passed to the script (Q3).
- Changed Retry-After to the seconds left in the minute from the Redis clock, instead of the key TTL, which would have expired 60 seconds after the first request and not at the minute boundary (Q9).
- Limited X-RateLimit headers to allowed responses, per requirement 6 (Q9).
- Added a failure table covering 401, 429, Redis failure, backend failure and Key Service failure.
- Moved Enterprise, Key Service outage, window edge and 429 headers into Open questions. No requirement was dropped.
- Restructured the file into the required order: summary, terms, diagram, steps, failure table, open questions. Removed the duplicate fail-open wording from the summary so the detail lives only in step 5 and the failure table.
- Added 'Backend' and 'Counter key' to the terms, because step 3 and step 4 use them and the junior could not tell which backend was meant (Q12, Q13).
- Step 1: stated that a revoked key keeps working and a plan change applies late, for up to 5 minutes, because of the cache (Q15).
- Step 3: stated that the gateway uses no clock for limits and that Retry-After and Remaining come from the script's reply (Q13).
- Step 4: stated that the check uses only customer ID and plan, so route lookup order does not change the outcome (Q12).
- Step 5: explained that the script may or may not have run, that a late answer still increments the counter, that nothing is replayed, and how the counter recovers when Redis returns (Q10, Q14).
- Failure table: added a row for backend timeout or unreachable, marked as undefined by the brief (Q11). Added a note to the fail-open row that the count may or may not include the request (Q10).
- Open questions: added backend timeout or unreachable, revoked keys and plan changes, and who receives the metric (Q11, Q15, Q16).
- Summary cut to three sentences: how the gateway works today, what the check adds, and why fail open keeps the API up. It also says that six instances do not multiply the limit and that a counter outage does not take the API down (requirements 7 and 8).
- Added one-line definitions for Retry-After and atomic-style behavior (in the Lua script and Redis terms). Added the reason for Redis (shared, can run one script as one step) and the reason for the fixed window, since the junior asked what each name and choice meant.
- Added short reasons at the step they apply to: the limit is passed in on each call, the TTL makes each minute use a new key, and a placeholder or Standard limit for Enterprise would set policy without Product.
- Step 3 now says the 50 ms is counted from when the gateway sends the call, and that the gateway's only clock is the 5-minute cache. Both were answered in the rounds and were not in the first version's steps.
- Merged repeated statements. The Enterprise skip is now stated once in step 2 and the header rules once in step 4. The 'no clock for limits' point is stated once in step 3. The fail-open count rules are grouped under step 5 instead of being repeated in the summary and the table.
- Steps now each stand alone, with the start, the action, the data kept and the failure behavior. The 'Key check' step states the 401 path and that Redis is untouched there.
- Added the sentence that the steps add only what the diagram cannot show, and kept the Mermaid diagram unchanged in form and branches. The diagram is placed after the summary and terms, as the diagram rule requires.
- Failure table kept as one table with the same six rows. Its wording was shortened, and the backend-timeout row now names the missing error definition.
- Open questions kept, each with the reason it is open. The Enterprise and Key Service items are unchanged in substance. The revoked-key item now also asks whether a cache-clear way is wanted (from the answer that the brief describes none).
- No stated fact was dropped: the 401/no-counter rule, 429 without use of budget, 500 counting, headers on passed requests, the 50 ms timeout, the late-answer rule, the 60 s TTL, the 100/min limit, Enterprise TBD, the 200-request window edge, the 429 header question and the metric name are all kept. No requirement or behavior was changed.

### Holes
- Q8: What happens if KeyService is slow or down? Is that also fail open, or does the request fail? (author: The brief does not say what the gateway does today when KeyService is slow or down, and this plan does not change it. Fail open (requirement 8) covers only the counter store. A request whose key cannot be resolved cannot be authenticated, so forwarding it would break requirement 3. This is listed as an open question to confirm.)
- Q11: What does the Gateway do with a Backend response when it's a timeout or the Backend is unreachable? The doc only mentions a 500 response. (author: The brief does not say what the client gets when the backend times out or cannot be reached, or whether the gateway sets a backend timeout at all. The request has already counted against the budget, as with a 500. Added as a table row and an open question.)
- Q15: What does the client see for a request whose key is cached for 5 minutes but has since been revoked or changed plan? Is there any way to invalidate the cache? (author: A revoked key keeps working, and a plan change applies late, for up to 5 minutes on each instance. The brief describes no way to clear the cache, so I do not know whether one exists or is wanted. Step 1 states the delay; the open question asks for confirmation.)
- Q16: Who receives the ratelimit_store_unavailable metric and is anything else done when it fires (alert, log)? (author: The brief says only to emit the metric. I do not know who receives it, or whether it also writes a log line or raises an alert. Added as an open question.)
