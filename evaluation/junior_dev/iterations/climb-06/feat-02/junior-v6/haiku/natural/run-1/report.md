## Review of feat-02 (junior-v6, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Rewrote the file for a newcomer: plain summary, terms, diagram, notes, failure table, open items. Removed the requirement and question codes so no step refers the reader elsewhere.
- Window: the gateway computes windowIndex and sets the key to expire at window end, not 60 s after its first request, so PTTL gives the true time to the next window. Lua argument changed to ms until window end (Q2, Q8).
- Retry-After source made consistent with the window key (Q2). Added the fallback Retry-After 60 when PTTL is not positive (Q8).
- Fail-open note now says a late reply is ignored and the script may still count (Q1).
- Added the backend-timeout-after-counting case to the notes and the failure table; the request still counts (Q3).
- Explained the three values the script returns and how the gateway reads them (Q4).
- Enterprise: named the metric ratelimit_enterprise_unlimited, emitted on each request while unset, defined an empty or absent config as not set, and no X-RateLimit headers while unlimited. Once a number is set, the Standard check applies with it (Q7).
- Stated how a plan change or revoked key takes effect (up to 5 minutes, existing cache) (Q6).
- Key Service behaviour and whether unknown answers are cached moved to open items instead of being assumed (Q5, Q6).
- Kept every stated fact from the first version: 6 instances, 100 per minute, 5-minute cache, 50 ms budget, X-Api-Key, 401, 429, Retry-After, headers, metrics, the open Enterprise limit, and the accepted risks.
- Changed: Customer note now says the cache is keyed by API key and each entry holds customer ID and plan, so the reader can see how keys share one budget (Q10).
- Changed: Store note now says the script sets the expiry in the same step as the first INCR, so no key lacks an expiry even if the gateway gave up (Q9).
- Changed: Window note now says the gateway computes windowIndex and ms-until-window-end on every call from its own clock, and the script uses the ms only when it creates the key (Q12).
- Changed: Retry-After note now says the PTTL is the time until the window ends, when the next window and a new count begin (Q12).
- Changed: Fail open note now says there is no circuit breaker in v1, so each request waits up to 50 ms while the store is slow, and this is accepted (Q14).
- Changed: Metrics note names the 429 counter ratelimit_denied with a plan label (Q13).
- Changed: Plan change open item now says each gateway instance has its own in-memory cache, so instances can change plan at different times within 5 minutes (Q11).
- Changed: Added an open item for the alert owner and threshold for ratelimit_store_unavailable, which the brief does not decide (Q13).
- Added a first paragraph that says how the gateway works today (no per-customer limit, 5-minute key cache, forwarding) before describing the change, and that the order of checks is fixed and why.
- Added a Terms section defining each term in one plain line: API Gateway, API key, Key Service, customer, plan, key cache, counter store, window, windowIndex, counter key, Lua script, PTTL, fail open.
- Kept the Mermaid sequence diagram from the previous version unchanged, with the summary and terms before it and the notes after it.
- Added a numbered list of the steps, in order, that maps the diagram's branches (401, Enterprise, store check, 429, forward, backend failure) so each step stands alone.
- Merged the Authentication-first and Customer-not-key notes into the steps and a one-line note each, and moved the Enterprise rules into one note.
- Merged the separate Metrics items into one note and listed the v1 settings (100/min, 50 ms, 5-minute cache, unset ENTERPRISE_LIMIT_PER_MIN) in one list.
- Clarified Retry-After: it is the PTTL measured by Redis, so it does not depend on the gateway clocks. Kept the fallback Retry-After: 60.
- Kept every stated fact from the previous version, including the Lua script, the failure table, the no-circuit-breaker decision, the late-reply rule, the 'counted even if the backend fails' rule, and all open items (Enterprise limit, alert owner and threshold, Key Service behaviour, unknown caching, client status on timeout, plan change lag, boundary burst, store failover).
- Removed repeated wording across the notes and the failure table; no rule was dropped.

### Holes
- Q5: What is the Key Service, and what does the gateway do today when it is down or slow on a cache miss? The notes say 'confirm with existing behaviour'. Can I assume a 401, a 5xx, or a pass-through? (author: Neither the brief nor the old file says what the gateway does today when the Key Service is down or slow on a cache miss. I did not assume a 401, a 5xx or a pass-through. It is listed as an open item.)
- Q6: The cache holds customerId and plan for 5 minutes. If a customer changes plan or a key is revoked, which limit applies during that time? Is 'unknown' cached too? (author: A plan change or a revoked key keeps its old limit until the 5-minute cache entry expires; that is how the existing cache works. Whether an "unknown" answer is cached at all is not stated, so I do not know. It is listed as an open item.)
