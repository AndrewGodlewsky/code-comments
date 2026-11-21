## Review of feat-02 (junior-v5, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a note in the diagram that Redis returns allowed+remaining or rejected+retryAfter (Q4).
- Marked the 429 as carrying no X-RateLimit headers, in the diagram and Headers section (Q8).
- Added an 'Existing behavior' paragraph: per-instance 5 min cache, up to 5 min staleness, only Standard and Enterprise plans (Q2, Q3).
- Clarified window unit as Redis seconds and that windows align to wall-clock minutes for all customers (Q6).
- Stated that the script is sent with each EVAL call, with nothing deployed to Redis ahead of time (Q4).
- Noted that Retry-After is computed inside the script from Redis time (Q8).
- Added to fail-open that a timeout after Redis ran the script may still spend one unit of budget, accepted (Q5).
- Added Open items for Key Service down/slow and for backend slow/unreachable, since the brief does not cover them (Q1, Q7).
- Enterprise limit: decided the gateway refuses to start while it is unset; updated the diagram note and open item (Q9).
- Window and overshoot: script computes windowStart itself, sets expiry in the same script on the first hit, key lives to window end plus 5 s (Q10, Q11).
- Existing behavior: noted instances may send different limits for up to 5 minutes after a plan change (Q12).
- Headers: remaining is 0 after the last allowed request and the next one gets 429 (Q13).
- Fail open: 50 ms covers the whole call, up to 50 ms delay per request during an outage, metric emitted once per failed request (Q14, Q15).
- Open items: added metric destination and logging as unknown (Q15).
- Added a 'Where the customer ID comes from' paragraph: only from the Key Service answer or cache (Q16).
- Added a line to Fail open: script errors and unexpected reply shapes are treated as unavailable and fail open (Q17).
- Added a 'Plan changes mid-window' paragraph: the count is kept and judged against the new limit; a lower limit than the count gives a normal 429 (Q18, Q19).
- Reordered: opening paragraph on how the gateway works today and what changes, then terms, then the diagram, then notes after it, per the diagram-form rule.
- Added a Terms section defining customer, plan, window, Redis time, Lua script and fail open in one line each.
- Merged the scattered Design decisions bullets (Store, Window, Overshoot, Counting, Retry-After, Plan changes) into one Check and count step with three numbered script actions.
- Merged the Where the customer ID comes from and Existing behavior paragraphs into the Resolve the key note, with the reason for each.
- Merged all fail-open lines into one Fail open note, keeping the 50 ms whole-call deadline, odd-reply rule, no circuit breaker and the timeout-after-run budget caveat.
- Added a short failure table; moved the 2x boundary trade-off after it.
- Split rollout (set Enterprise limit before deploy, add alert) out of how the system runs into a Rollout section.
- Cut the separate Store and Window headings, the Redis time clock-skew rationale restated in several places, and the repeated requirement references.
- Moved the alerting item from Open items into Rollout; Open items keep only genuine unknowns.
- Diagram unchanged.

### Holes
- Q1: What does the Key Service do if it is down or slow, and what happens to the request then? Is that different from an unknown key? (author: Not known. The brief does not say what the gateway does today when the Key Service is down or slow, and I have not checked. It is separate from an unknown key (which is 401). Added to Open items; this design adds nothing for it.)
- Q7: What happens if the backend is slow, times out, or is unreachable? Does the gateway return its own error, and what does the client see with regard to the X-RateLimit headers? (author: The brief does not say how the gateway handles a slow, timed-out or unreachable backend, and I have not checked the gateway code. The request has already counted. Whether the gateway's own error response carries X-RateLimit headers is undecided. Added to Open items.)
- Q15: Who receives the ratelimit_store_unavailable metric, and is it emitted once per failed request? Is anything logged besides the metric? (author: Not known which metrics system receives it or whether anything is logged; the brief does not say and I have not checked the gateway. It is emitted once per failed check. Added an open item to use the gateway's existing metrics and logging.)
