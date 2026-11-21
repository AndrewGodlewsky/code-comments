## Review of feat-02 (junior-v7, author sonnet, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Rewrote the document in the required order: summary, terms, flow diagram, notes, failures table, open questions.
- Added how the system works today (6 stateless instances, Key Service with 5-minute cache, forwarding).
- Expanded the diagram with the Key Service reply, 401, 429, allowed and fail-open branches so it shows where the Backend is skipped.
- Defined the fixed clock-minute window, counter key name rl:{customerId}:{minute}, and 120 s TTL.
- Specified check_and_incr input, output and no-increment-when-rejected behavior.
- Defined Retry-After as seconds to the end of the minute (min 1).
- Decided fail-open responses omit X-RateLimit headers; 50 ms is a per-call timeout.
- Added failures table and open questions for the Enterprise limit and Key Service outage behavior.
- Noted the fixed-window boundary burst trade-off.
- Limit note: added that a plan change applies only after the 5-minute cache expires (Q11).
- check_and_incr note: added that an existing count is kept and compared with the new limit if the limit changes mid-minute (Q12).
- Failures table: added that a request whose Redis call timed out may still be counted, accepted (Q10).
- Open questions: made Enterprise behavior explicit as undecided (Q9) and added whether the key cache holds unknown keys (Q11).
- Rewrote opening summary to add the fail-open outcome in one sentence
- Added Terms entries for Lua script and Fail open (newcomer-level names)
- Folded the 120-second expiry reason into the Window term ('old counters clean themselves up')
- Restructured check_and_incr note into sub-bullets (rejected, allowed, never resets) for readability; same facts
- Merged 'Counter keys have a TTL' and expiry mentions so the 120 s fact appears once in Window plus once where the script sets it
- Added reason for not invalidating the cache on plan change (no new mechanism)
- Added in Retry-After that it is computed in the script from Redis time
- Headers note now points to the fail-open exception instead of leaving it only in the table
- Failures table: stated 50 ms is per single call, added the reason for omitting headers and for accepting the double-count (no retry or queue)
- Open questions: stated that no limit value is passed to check_and_incr for Enterprise
- Cut nothing stated in the brief; all 8 requirements, limits and numbers retained

### Holes
- Q8: What happens if KeyService is slow or down? The notes only cover Bad key and Redis failure. (author: The brief does not say how the Key Service behaves when slow or down, and this feature does not change that path. It is whatever the Gateway does today (the 5-minute cache helps for recently seen keys). Added to open questions rather than guessing.)
- Q9: When an Enterprise customer's request arrives today, what does the Gateway actually do: skip the check, apply Standard's 100, or reject? What limit value is passed to check_and_incr? (author: Not decided. The brief says Product has not set the Enterprise limit and I must not pick a number, and it gives no fallback behavior (skip, reject or reuse 100). So no value is passed for Enterprise yet. Added to open questions that the Enterprise behavior is undecided.)
- Q11: Does the 5-minute cache hold only valid keys, or also unknown keys? What happens to the limit if a customer's plan changes within those 5 minutes? (author: Whether the cache holds unknown keys is not known: the brief only says the Gateway caches the Key Service answer for 5 minutes. Added to open questions. On plan changes: the Gateway uses the cached plan, so the old plan's limit can apply for up to 5 minutes. I accept that staleness because it follows from the existing cache and avoids a new invalidation mechanism. Noted under Limit.)
