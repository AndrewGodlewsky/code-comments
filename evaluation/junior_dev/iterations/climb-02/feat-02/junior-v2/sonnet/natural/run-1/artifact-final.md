# Per-customer rate limiting on the public API: design

## Decisions

- **Store:** one shared Redis instance (with a replica for failover) holds all counters. All 6 gateway instances use it, so counts are shared (req. 7).
- **Window:** fixed one-minute window aligned to the clock. Key: `rl:{customerId}:{floor(now/60)}`, expiring 120 s after the first increment. A fixed window allows up to 2x the limit across a window boundary. We accept this for a first version.
- **Atomicity:** the gateway calls one Lua script on Redis, passing `customerId` and `limit`. The script builds the key itself from Redis `TIME` (so gateway clock skew cannot matter) and runs as a single step, so concurrent requests on different instances cannot overshoot:
  1. Read the current count `c` (0 if the key does not exist).
  2. If `c >= limit`, return `DENY` with the seconds left in the window. Do not increment (req. 4).
  3. Otherwise `INCR` the key. If `INCR` returns 1, set the 120 s expiry. Return `ALLOW` with `remaining = limit - (c+1)`.
- **Retry-After:** seconds until the current window ends, rounded up, never below 1.
- **Limits:** the plan from the Key Service picks the limit from a config table. Standard is 100 per minute. **Enterprise is OPEN: product has not decided, and the table entry is unset.** While a plan has no limit, its requests skip the rate-limit check: they are not counted, are forwarded, and get no `X-RateLimit-*` headers. Do not guess a value in code. Product must decide before launch.
- **Per customer:** the counter key uses the customer ID from the Key Service, never the API key (req. 1).
- **Headers:** `X-RateLimit-Limit` is the customer's limit per minute. `X-RateLimit-Remaining` is how many more requests fit in the current window after this one. They go on passed requests only, except that 429 responses also carry `X-RateLimit-Limit` and `X-RateLimit-Remaining: 0`.
- **Fail open (req. 8):** the Redis call has a 50 ms timeout. On error or timeout the gateway forwards the request, emits `ratelimit_store_unavailable`, sends **no** `X-RateLimit-*` headers (the real values are unknown) and does not retry. If the script still ran after the gateway gave up, its increment is kept.
- **Backend failures:** the count is incremented before forwarding and never rolled back, so a backend 500 still uses budget (req. 5). The backend response is returned as the gateway does today.

```mermaid
sequenceDiagram
    autonumber
    actor C as Client
    participant G as API Gateway (any of 6)
    participant K as Key Service
    participant R as Redis (shared counters)
    participant B as Backend service

    C->>G: Request with X-Api-Key
    Note over G: Key to customer and plan is cached in memory for 5 min, separately on each instance
    G->>G: Look up key in cache
    alt Cache miss
        G->>K: Resolve key
        K-->>G: customerId + plan, or unknown
    end

    alt Key missing or unknown
        G-->>C: 401 Unauthorized
        Note over G,R: Rate-limit store is never touched
    else Key valid
        Note over G: limit = table[plan]. Standard = 100/min, Enterprise = OPEN (undecided)
        alt No limit set for plan (Enterprise today)
            G->>B: Forward request, no check, no counting
            B-->>G: Response
            G-->>C: Backend response, no X-RateLimit headers
        else Limit set
            G->>R: Lua script, 50 ms timeout: check and increment (customerId, limit)

            alt Store error or no answer within 50 ms
                G-)G: Emit metric ratelimit_store_unavailable
                Note over G: Fail open. No X-RateLimit headers, counts unknown
                G->>B: Forward request
                B-->>G: Response (any status)
                G-->>C: Backend response, unchanged
            else DENY (count already at limit)
                R-->>G: DENY, secondsLeftInWindow
                Note over R: Count not incremented
                G-->>C: 429 Too Many Requests, Retry-After: secondsLeft
                Note over G,B: Request is not forwarded
            else ALLOW (count incremented)
                R-->>G: ALLOW, remaining
                G->>B: Forward request
                B-->>G: Response (including 500)
                Note over R,G: Budget stays used even if the backend failed
                G-->>C: Backend response + X-RateLimit-Limit + X-RateLimit-Remaining
            end
        end
    end
```

## Notes

- **Overshoot:** Redis runs a script to completion before the next one, so two instances cannot both see 99 and both pass.
- **Cache staleness:** a plan change can take up to 5 minutes to take effect, because of the existing key cache. Acceptable.
- **Redis failover:** a failover may lose the last few increments, so a customer could briefly get a little extra budget. Acceptable for a first version.
- **Out of scope:** sliding windows, per-route limits, and burst allowances.

## Open questions

- Enterprise limit: product has not decided. Until then Enterprise traffic is unlimited (see Limits).
- Existing behavior this design does not change and the author has not verified: what the gateway does when the Key Service is down or slow on a cache miss, whether unknown keys are cached, and what the client sees if the backend is unreachable or times out.
