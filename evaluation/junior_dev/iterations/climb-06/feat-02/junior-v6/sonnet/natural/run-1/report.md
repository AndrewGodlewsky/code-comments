## Review of feat-02 (junior-v6, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Restructured into summary paragraph, terms, diagram, per-part notes, failure table, trade-offs and open questions, as the skill's layout requires
- Added a Terms section defining customer, plan, Key Service, Redis, Lua script, window and fail open
- Spelled out the first-request behaviour in the script: missing key counts as 0, INCR creates it, expiry is set in the same script
- Stated that only Redis time is used, never gateway time
- Added Key Service outage handling: 503 and no forward (my decision, flagged in Open questions)
- Stated that Remaining is 0 on the request that takes the last slot
- Stated that a timed-out Redis call is not retried and any increment it made stays counted
- Added a failure table and noted cache staleness for revoked keys
- Added open questions on unknown-key caching and Redis failover; kept the Enterprise limit open
- Backend failure bullet now says an unreachable or too-slow backend gives 502 or 504, still counted, with X-RateLimit headers, no retry (answers Q9).
- Added a table row for backend unreachable or too slow.
- Authentication bullet and table row now say Key Service error or no answer gives 503 with no retry (answers Q10).
- Open questions: Key Service timeout value is unknown and to be confirmed; added backend 502/504 codes as my choice to confirm.
- Counter key: stated that the script builds the key and window start from Redis TIME, and the gateway sends only customerId and limit (Q11).
- Lua script step 1: now says it also sets windowStart and builds the key (Q11).
- Headers: stated that the gateway adds them itself from the script's remaining value and its own limit, that values are plain integers, that no reset header is added, and that 429 carries Retry-After (Q12, Q14).
- Cache: added that gateways cache separately, so limits can briefly differ after a plan change, and the script uses the limit passed in per call (Q13).
- Open questions: added the alerting and ownership gap for ratelimit_store_unavailable (Q15).
- Restructured into: summary paragraph, terms, diagram (unchanged), numbered steps in order, failure table, trade-offs, open questions.
- Replaced the loose 'What each part does' bullets and the old Decisions/Notes split with seven ordered steps; each says what it does, what keeps the data and what happens on failure.
- Merged Counter key, Check and increment and the window-clock explanation into one Lua-script step; merged Headers and Backend failure into the ALLOWED step.
- Merged the separate cache/plan-staleness, per-gateway limit difference and revoked-key notes into one 'Cache effects' step.
- Split the backend failure row into two (502 refused/reset, 504 timeout) in the table; moved the no-retry reason (non-idempotent) next to it.
- Cut the repeated Enterprise explanation (kept once in step 3 plus the open question) and the repeated 'Authentication first' wording.
- Kept all original facts: 6 instances, 5-min cache, 100/min Standard, Enterprise open, 120s expiry, Redis TIME, 50 ms timeout, headers, 429/Retry-After, metric name, window-edge burst, latency, lost keys, primary plus replica.
- Dropped the unneeded details the junior asked about (exact header formats beyond plain integers, no reset-time header kept as one clause); answers stay in the report.
- Added Redis failover and alerting questions as open items; Key Service timeout still unknown.

### Holes
- Q3: What does the cache do with a key the Key Service said was unknown? Is that cached too, and what if a key is revoked during the 5 minutes? (author: It is not known whether the existing cache stores unknown-key answers; that is in Open questions. A key revoked during the 5 minutes keeps working until its cache entry expires, the same staleness as a plan change. Accepted for v1.)
- Q7: The doc says primary plus replica for availability. If the primary fails, does the replica take over automatically, and what happens to counters during that switch? (author: The brief does not say how failover works, and I do not know whether it is automatic. Replication is likely asynchronous, so a switch can lose the latest increments, giving customers a brief fresh budget, the same as lost keys. This is in Open questions and Known trade-offs.)
- Q10: How slow is 'slow' for the Key Service? Is there a timeout, and does the gateway retry before it returns 503? (author: The Key Service timeout is not known; the brief does not give one and I have not seen the gateway's existing client config. My decision: reuse whatever timeout the gateway's current Key Service call has, do not retry, and return 503 on error or timeout. The actual timeout value is in Open questions to confirm.)
- Q15: What alerts on-call when ratelimit_store_unavailable fires, and who owns that alert? Is it already set up, or just a recommendation? (author: I do not know. The brief names no alert or owner, and I have not seen the monitoring setup. The doc only recommends that the metric alert on-call. I added an open question that an alert and an owner must be set up before launch.)
