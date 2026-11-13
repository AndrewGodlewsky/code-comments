# Per-customer rate limiting on the public API (v1 design)

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant G as API Gateway (any of 6 instances)
    participant K as Key Service
    participant R as Counter store (Redis)
    participant B as Backend service
    participant M as Metrics

    C->>G: Request with X-Api-Key
    alt Header missing
        G-->>C: 401 Unauthorized (no counter touched)
    else Header present
        G->>G: Look up key in local cache (5 min TTL)
        opt Cache miss
            G->>K: Resolve key
            K-->>G: customerId and plan, or unknown
        end
        alt Key unknown
            G-->>C: 401 Unauthorized (no counter touched)
        else Key valid
            Note over G: Authenticated. Budget is keyed by customerId, not by key.
            G->>R: Atomic check-and-reserve script (rl:customerId:minute, limit, 60s), timeout 50 ms
            alt Store error or no reply within 50 ms
                G->>M: ratelimit_store_unavailable
                Note over G: Fail open. No X-RateLimit headers on this response.
                G->>B: Forward request
                B-->>G: Backend response (any status)
                G-->>C: Backend response
            else Store answered: under limit
                R-->>G: allowed, new count, limit, retry info
                Note over R: Count was reserved before forwarding, so a backend 500 still uses budget.
                G->>B: Forward request
                B-->>G: Backend response (any status)
                G-->>C: Backend response plus X-RateLimit-Limit and X-RateLimit-Remaining
            else Store answered: at or over limit
                R-->>G: denied, seconds until window reset
                Note over G: Never forwarded. Count was not incremented, so the 429 uses no budget.
                G-->>C: 429 Too Many Requests plus Retry-After in seconds
            end
        end
    end
```

## Notes

**Limits and open decision.** Standard customers get 100 requests per minute. The Enterprise limit is **OPEN: awaiting product decision.** The design reads the limit from plan configuration, so the number can be filled in later without changing the flow.

**Store.** Use Redis (or any store with atomic server-side scripts and a single clock). All gateway instances share one counter per customer, so spreading a customer over 6 instances does not multiply their limit (requirement 7).

**Window.** A fixed window. The key is `rl:<customerId>:<floor(unixSeconds / 60)>` with a 60-second expiry. Budget resets at each minute boundary. Known trade-off: a customer can send up to about 2x the limit across a boundary (for example 100 at 0:59 and 100 at 1:00). A sliding window is the upgrade path if this matters.

**No overshoot across instances.** The check-and-increment runs as one Lua script, so Redis executes it atomically. The script runs in this order:

1. Read the current count.
2. If the count is below the limit, increment it and return allowed with the new count.
3. Otherwise return denied and leave the count unchanged.

Do not use a separate INCR-then-compare. That would count rejected requests against the budget and break requirement 4.

**Retry-After.** The script reads Redis `TIME` and returns the seconds until the window key expires. The gateway sends that value, rounded up, with a minimum of 1.

**Remaining.** `X-RateLimit-Remaining` is `limit - newCount`. `X-RateLimit-Limit` is the customer's plan limit.

**Fail open.** The store call has a 50 ms timeout, and any error also counts as a failure. On failure the gateway emits `ratelimit_store_unavailable` and forwards the request without rate-limit headers. A rejection that was not seen because of a timeout can therefore pass through. This is accepted by requirement 8.

**Auth first.** Missing or unknown keys return 401 before any store call, so the 401 path cannot read or change a counter (requirement 3).

**Cache lag.** The 5-minute key cache means a plan change or a new key can take up to 5 minutes to take effect. A new customer ID is picked up on the first request for an uncached key. Acceptable for v1.

**Not in v1.** Per-route limits, burst allowances, per-IP limits, and a dedicated rate-limit service are out of scope.

## Open questions

1. **Enterprise limit:** OPEN, awaiting product decision.
2. Should a fail-open response carry any rate-limit header, or none at all? This design sends none.
