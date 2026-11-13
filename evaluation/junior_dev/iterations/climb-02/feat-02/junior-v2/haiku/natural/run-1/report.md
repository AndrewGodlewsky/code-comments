## Review of feat-02 (junior-v2, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a Key Service failure branch (503, not forwarded, no count) to the diagram and notes (Q1).
- Added a backend-failure branch to the diagram: a 500 passes through, and a failure or timeout gives the gateway's 502/504, with headers on either (Q5).
- Stated that the limit comes from a per-plan gateway config and is passed as ARGV[1] (Q3).
- Stated that Remaining = limit - count, where count is the value returned after the increment (Q4).
- Explained that the Lua script is one atomic call and one round trip (Q6).
- Stated which clock each gateway uses for windowStart and Retry-After, plus the NTP requirement (Q2, Q7).
- Stated that missing and unknown keys return the same 401 (Q8).
- Added a Key Service failure row to the decisions table.
- Cut the open item about metrics for denied requests. It was optional and outside the brief, and it is not needed to follow the main flow. Cut the circuit-breaker sentence from the plan-changes note and kept it only in the fail-open note.
- Merged the Summary and Window notes so each rule appears once.
- Fail open: removed the claim that nothing is counted. A timed-out request may already have been counted by the store, and it is forwarded either way (Q9). Diagram store-timeout label now says it may still have counted.
- Authentication and Plan changes: the cache is the gateway's own in-memory cache per instance, not the Key Service's cache. Diagram Key Service label updated to match (Q10).
- Authentication and Backend failure: Key Service and backend timeouts are marked as not set and moved to open item 4 (Q11).
- Denied 429: now carries Retry-After only, with no X-RateLimit headers. Updated the Retry-After paragraph, the Denied diagram branch and the Decisions table (Q12).
- Open item 4 added for timeouts and for the metrics destination and alerting of ratelimit_store_unavailable, which the brief does not cover (Q13).
- Window and clock: added how two gateways straddling a boundary through skew can use different keys, and that the extra budget lasts only for the skew interval (Q14).
- Decisions table: Fail-open row now says the store may or may not have counted the request. Added a Denied response row. Store timeout row points to open item 4 for the other timeouts.
- Removed the Decisions table. Every row was already stated in its step section (counter store, key, window, concurrency, Retry-After, denied response, fail-open response, Key Service failure, store timeout), so it said everything twice.
- Merged the Identity section into the Limit section as 'Identity and limit'.
- Merged the counter-store choice (Redis, other stores also work) into the Check and count step, next to the atomic-script explanation.
- Merged the Retry-After rule and the 'no X-RateLimit headers on 429' rule into one Denied (429) step.
- Stated the boundary-burst tradeoff once, in the Window step, and cut it down to a pointer in open item 3. It was previously repeated in the window text and the open items.
- Shortened the Fail open step: merged the 'cannot know whether it counted' explanation with the 'nothing is rolled back' note, and kept the client-facing rule and the circuit-breaker exclusion.
- Shortened the Summary and the Authentication step, and cut sentences that repeated the sequence diagram.
- Shortened open items 2 to 4 to one line each, with pointers to the step where the behaviour is described. Open item 1 and the 'must not ship' rule are kept.
- No behaviour, limit, header, or status code was changed. The sequence diagram and the Lua script are unchanged.

### Holes
- Q11: What is the gateway's timeout for the Key Service call, and for the backend call? The document gives 50 ms only for the store. (author: The brief gives no timeout for the Key Service call or for the backend call. Only the 50 ms store timeout is set. I have no reason I can defend for specific values, so I did not invent any. Both are listed as open item 4 for the team to choose.)
- Q13: What does the metric ratelimit_store_unavailable go to, and does anyone get alerted when it fires? Who notices a long outage where nothing is limited? (author: The brief names no metrics system and no alert. v1 only emits the metric. Nothing in this design pages anyone, so a long store outage means no limits apply and no one is told. The team must choose a destination and an alert rule. This is open item 4.)
