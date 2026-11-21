# Per-customer rate limiting on the public API

## Summary

Today every public request goes through the API Gateway: 6 stateless instances behind a load balancer, any of which can take any request. The gateway reads the `X-Api-Key` header and asks the Key Service which customer and plan it belongs to. It keeps each answer in that instance's own memory for 5 minutes. It then forwards the request to the backend that owns the route and returns the backend's response.

This change adds a rate-limit check between "key resolved" and "forward". The gateway asks one shared Redis for a verdict. Redis counts requests per customer in fixed one-minute windows. Over the limit, the client gets `429` and the request is never forwarded. If Redis fails or is slow, the gateway forwards the request anyway, so a counter outage cannot take the API down. The design is deliberately simple: it is a first version.

## Terms

- **Customer**: the account that owns one or more API keys. Limits apply per customer, so all of a customer's keys share one budget.
- **Plan**: Standard or Enterprise. It comes from the Key Service. Standard allows 100 requests per minute. The Enterprise number is not decided (see Open items).
- **Window**: one wall-clock minute, for example 12:03:00 to 12:03:59. Every customer's windows start at the same moments. A window does not start at a customer's first request.
- **Redis time**: Redis's own clock in whole seconds, read with `TIME`. All window maths uses it, so gateway clock differences never matter.
- **Lua script**: a small program that Redis runs as one indivisible step. No other command runs in the middle of it. This is what stops two instances taking the last slot at once.
- **Fail open**: when the counter store is broken, let the request through instead of blocking it.

## How a request flows

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant G as API Gateway (any of 6 instances)
    participant K as Key Service
    participant R as Redis (shared counters)
    participant B as Backend service
    participant M as Metrics

    C->>G: Request with X-Api-Key
    G->>K: Resolve key (served from 5 min in-memory cache when present)
    K-->>G: customerId and plan, or unknown

    alt Key missing or unknown
        G-->>C: 401 Unauthorized
        Note over G,R: No rate-limit counter is read or changed
    else Key valid
        Note over G: limit = 100 if Standard, ENTERPRISE LIMIT TBD (Product undecided; gateway will not start without it)
        G->>R: EVAL check_and_incr(customerId, limit), 50 ms timeout
        Note over G,R: Redis returns allowed and remaining, or rejected and retryAfter

        alt Redis errors or no answer within 50 ms (fail open)
            G->>M: emit ratelimit_store_unavailable
            G->>B: Forward request
            B-->>G: Response (any status)
            G-->>C: Backend response, no X-RateLimit headers
        else Over limit (count >= limit, nothing incremented)
            R-->>G: rejected, retryAfter seconds
            G-->>C: 429 Too Many Requests, Retry-After: retryAfter, no X-RateLimit headers
            Note over G,B: Never forwarded, and a 429 uses no budget
        else Under limit (count incremented atomically)
            R-->>G: allowed, remaining
            G->>B: Forward request
            B-->>G: Response (including 500)
            G-->>C: Backend response plus X-RateLimit-Limit and X-RateLimit-Remaining
            Note over G,R: Budget is not refunded if the backend failed
        end
    end
```

## Notes on each step

**Resolve the key (steps 2-3).**
- The customer ID comes only from the Key Service answer or its cache, never from the request. Otherwise a client could spend another customer's budget.
- The cache is per instance. A revoked key or changed plan can go unnoticed for up to 5 minutes. That is how the gateway works today and this design leaves it alone.
- Because the limit sent to Redis comes from the cached plan, two instances may briefly send different limits for one customer. Each call is judged against the limit it sends.
- A missing or unknown key gets `401` before any Redis call.

**Check and count (steps 5-6).** The gateway sends Redis only the customer ID and the limit, using `EVAL` with the script text each time. Redis caches the script, and nothing is installed on Redis ahead of time. The script does this as one step:
1. Compute `windowStart = floor(redisTime / 60)`. The counter key is `rl:{customerId}:{windowStart}`. It has no plan or key in it.
2. Read the count. If `count >= limit`, return "rejected" with `retryAfter` and change nothing.
3. Otherwise `INCR` the count. If the new count is 1, set the key to expire at the window's end plus 5 seconds, so old counters clean themselves up. Return "allowed" with `remaining = limit - newCount`.

Counting happens here, before forwarding. So a request that passes the check uses budget even if the backend then returns 500.

**Retry-After.** On rejection the script returns the seconds left in the window (`windowEnd - redisTime`), rounded up, at least 1. The count resets at the next window, so a retry after that long will succeed. The gateway sends this value as `Retry-After`.

**Plan change in mid-window.** The count in the current window is kept and judged against whatever limit the next call sends. If a downgrade puts the limit below the count, the script simply rejects, with `Retry-After` as above. No special case is needed.

**Response headers.** `X-RateLimit-Limit` is the plan limit. `X-RateLimit-Remaining` is the script's `remaining`, so it is 0 after the last allowed request, and the next request in that window gets a `429`. Both headers go on every response that passed the check, whatever the backend status. `429` responses and fail-open responses do not carry them.

**Fail open (steps 4 and 7-10).**
- The Redis call has one 50 ms deadline for the whole call, including connecting. An error, a timeout, a script error, or a reply that is not one of the two expected shapes all count as "unavailable".
- The gateway then forwards the request normally and emits `ratelimit_store_unavailable` once for that request. No `X-RateLimit-*` headers are added, because the real remaining count is unknown.
- No retry, no local fallback counter and no circuit breaker. During an outage the limit is not enforced, and each request may wait up to 50 ms before being forwarded.
- If the timeout fires after Redis already ran the script, that request may have used one unit of budget while being forwarded without headers. This is accepted as rare and cheap.

## What happens when things fail

| Where | What happens |
|---|---|
| Key missing or unknown | `401`. No counter is touched. |
| Redis error, timeout or odd reply | Fail open: forward, emit the metric, no headers. |
| Over the limit | `429` with `Retry-After`, not forwarded, no budget used. |
| Backend returns 500 | Passed to the client with the `X-RateLimit-*` headers. The request stays counted. |

Known trade-off: a fixed window lets a client send up to 2x the limit across a window boundary (100 at 0:59, 100 at 1:00). Accepted for a first version. A sliding window is a later option.

## Rollout

- Set the Enterprise limit in config before deploying. It has no default, and the gateway refuses to start while it is unset, so no Enterprise request is ever judged against a guessed number.
- Set up an alert on `ratelimit_store_unavailable`, since fail-open hides outages from clients.

## Open items

- **Enterprise limit:** Product has not decided. Do not pick a number.
- **Redis availability:** whether to run a replica or failover is not covered here.
- **Metric destination and logging:** which metrics system receives `ratelimit_store_unavailable`, and whether a log line is also written, is not known. Use what the gateway already uses.
- **Key Service down or slow:** not covered by the brief. What the gateway does today is not known, and this design adds nothing for it.
- **Backend slow, timing out or unreachable:** not covered by the brief. The gateway's existing error handling applies. The request already counted. Whether that error response carries the `X-RateLimit-*` headers is not decided.
