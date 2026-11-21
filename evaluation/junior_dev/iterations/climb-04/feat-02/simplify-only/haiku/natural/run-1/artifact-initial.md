# Per-customer rate limiting on the public API

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant G as API Gateway (6 stateless instances)
    participant K as Key Service
    participant R as Counter store (Redis)
    participant B as Backend service
    participant M as Metrics

    C->>G: request with X-Api-Key
    G->>K: resolve key (skipped on in-memory cache hit, 5 min TTL)
    alt key missing or unknown
        K-->>G: not found
        G-->>C: 401 Unauthorized
        Note over G,R: No counter is read or written
    else key valid
        K-->>G: customerId, plan
        G->>G: limit = limitFor(plan), Standard 100, Enterprise OPEN
        alt Enterprise limit not set (OPEN, see note 2)
            Note over G: Placeholder only, pending Product decision
            G->>B: forward without check or headers
            B-->>G: backend response
            G-->>C: backend response
        else limit known
            G->>R: EVAL check and increment for customerId, limit, window 60 s, timeout 50 ms
            alt store error or no answer within 50 ms
                R--xG: error or timeout
                G->>M: emit ratelimit_store_unavailable
                G->>B: forward request (fail open)
                B-->>G: backend response, including 5xx
                G-->>C: backend response, no X-RateLimit headers
            else store answered
                R-->>G: allowed, count, ttl_ms
                alt over limit (rejected, nothing counted)
                    G-->>C: 429 Too Many Requests, Retry-After = ceil(ttl_ms / 1000)
                    Note over G,B: Not forwarded, no budget used
                else allowed (already counted)
                    G->>B: forward request
                    B-->>G: backend response, including 5xx
                    G-->>C: backend response, X-RateLimit-Limit, X-RateLimit-Remaining = limit - count
                    Note over G,B: Count stays even if backend fails
                end
            end
        end
    end
```

## Notes

1. **Counter scope and store.** One counter per customer, keyed `rl:<customerId>`. The customerId comes from the Key Service answer, so all keys of a customer share one budget (requirement 1). Redis is the shared store (requirement 7). All six instances read and write the same key, so spreading traffic across instances does not multiply the limit.

2. **Enterprise limit is OPEN.** Product has not chosen a number, and this design does not pick one. `limitFor(plan)` returns Standard = 100 per minute and has no value for Enterprise. Proposed for v1, for Product to confirm: Enterprise traffic skips enforcement (no counter, no headers) behind a config flag, so the open decision does not block launch. The gateway must not guess a value.

3. **Window.** A fixed 60 s window. The window starts at a customer's first counted request, and the key's TTL is the window end. This is the simplest option. Known trade-off: a customer can send up to about 2x the limit across a window boundary. A sliding window is a later upgrade if that matters.

4. **Atomic check and increment.** One Redis script runs the check and the increment together, so two instances cannot both see 99 and both pass. Rejected requests are not incremented, which satisfies requirement 4.

   ```lua
   -- KEYS[1] = rl:<customerId>   ARGV[1] = limit   ARGV[2] = window seconds
   local count = tonumber(redis.call('GET', KEYS[1]) or '0')
   if count >= tonumber(ARGV[1]) then
     return {0, count, redis.call('PTTL', KEYS[1])}   -- rejected, not counted
   end
   count = redis.call('INCR', KEYS[1])
   if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
   return {1, count, redis.call('PTTL', KEYS[1])}
   ```

5. **Retry-After.** Computed from Redis PTTL, so gateway clock skew does not matter. Retry-After = ceil(ttl_ms / 1000), with a minimum of 1 second. On a 429 the gateway also sends `X-RateLimit-Limit` and `X-RateLimit-Remaining: 0` (my choice, optional).

6. **Fail open.** The gateway sets a 50 ms timeout on the store call, which covers both errors and slow answers. On failure it forwards the request, emits `ratelimit_store_unavailable`, and omits the X-RateLimit headers, because the check did not run. A timed-out INCR may still apply in Redis, so a count can be off by one. This is accepted for v1. Alert on the rate of `ratelimit_store_unavailable`.

7. **Ordering.** A 401 happens before any store access (requirement 3). The check runs after authentication and before forwarding (requirement 4). A backend failure does not refund budget (requirement 5).

8. **Plan changes.** The Key Service answer is cached for 5 minutes, so a plan change takes up to 5 minutes to apply.

## Open items

- Enterprise limit value, owned by Product (note 2).
- Confirm the enforcement-skip placeholder for Enterprise, or choose another v1 behavior.
- Redis deployment and failover are not covered here.
- Per-route limits are not in scope for v1.
