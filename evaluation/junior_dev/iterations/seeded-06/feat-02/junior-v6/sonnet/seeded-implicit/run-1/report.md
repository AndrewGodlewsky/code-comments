## Review of feat-02 (junior-v6, author sonnet, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Rewrote the document in the skill's order: summary with how the system works today, terms, a fuller diagram, numbered steps, a failure table, open questions.
- Diagram now shows the 401, 429, fail-open and success paths with alt blocks, and that each call waits for the previous one.
- Defined the counter key, the fixed calendar minute from Redis's clock, the 120 s TTL and why, and what check_and_incr returns.
- Stated that rejected requests are not counted, and that Retry-After is the whole seconds until the next minute.
- Stated how the plan reaches the limit (Key Service result mapped to gateway config).
- Stated that fail open sends no X-RateLimit headers and that 429s carry only Retry-After.
- Noted the fixed window boundary burst as an accepted limit.
- Added Open questions for the Enterprise limit and for Key Service slow or down.
- Step 2: added the handling for Enterprise while no limit is set (skip check, forward uncounted, no headers), and listed it for Product to confirm.
- Step 3: spelled out how remaining and seconds-until-next-minute are calculated and that both use Redis's clock.
- Terms: Window now says minute number is Redis clock seconds divided by 60, rounded down.
- Failure table: explained how a fail-open request may or may not be counted and that nothing corrects it; added a row for a long Redis outage (tries every request, no circuit breaker).
- Open questions: added that client behavior on a failed uncached Key Service lookup is undefined, and that negative caching and revocation delay are unstated.
- Rewrote the opening paragraph to state purpose (one noisy customer must not degrade others), the main flow, and that 6 instances sharing Redis do not give 6x the limit.
- Added to the Terms: budget belongs to the customer not the key; Redis keeps the counters and the gateway keeps none; fail open's purpose (a counter outage must not take the API down).
- Step 1: added what key resolution takes as input and returns, and a pointer to Open questions for Key Service failures.
- Step 2: added why no new lookup is needed (the plan arrives with the customer ID).
- Step 3: split the allowed and rejected outcomes into two bullets and moved the Redis-clock sentence to the start so the minute number and seconds-left source is clear.
- Moved the rule that the 429 carries no X-RateLimit headers into step 4; step 5 now says the headers also go on backend error responses.
- Fail-open row: added that the gateway cannot tell whether the request was counted and that the error is at most one request in one minute's counter.
- Long-outage row: added the up to 50 ms extra latency and the reason for no circuit breaker.
- Fixed-minute note: added the up to 2x boundary burst and the reason it is accepted.
- Open questions: reworded the Key Service item to match the brief; kept all three items.
- Cut the repeated 'steps wait for each other' detail down to one sentence; left out exact script format and other details nothing asked for. All first-version facts were kept, including the fixed requirements: 401 before counters, 429 with Retry-After in seconds, 100 per minute for Standard, 50 ms timeout, the metric name, and both headers.

### Holes
- Q10: When the Key Service answer is not in the 5-minute cache, does the gateway call it on that request and wait? What does the client see if that lookup fails or times out? (author: The brief does not say how the gateway handles a cache miss or a failing Key Service lookup today, so I do not know what the client sees. Listed under Open questions.)
- Q11: Are 'not found' answers for unknown keys also cached for 5 minutes? And if a customer's plan changes or a key is revoked, does the old answer keep applying until the cache expires? (author: The brief says the gateway caches the answer for 5 minutes but not whether 'not found' is cached. A plan change or revocation would follow the same cache, so an old answer can apply until it expires, but I have not verified this. Listed under Open questions.)
