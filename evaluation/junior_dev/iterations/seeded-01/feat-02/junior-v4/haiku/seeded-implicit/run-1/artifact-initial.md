## Rate limiting

Per-customer rate limiting in the API Gateway, backed by Redis.

```mermaid
sequenceDiagram
    participant Client
    participant Gateway
    participant KeyService
    participant Redis
    participant Backend
    Client->>Gateway: request
    Gateway->>KeyService: resolve key
    Gateway->>Redis: check_and_incr
    Gateway->>Backend: forward
    Backend-->>Gateway: response
    Gateway-->>Client: response
```

Notes:
- check_and_incr is a Lua script. Counters are per minute.
- Counter keys have a TTL.
- Limits: Standard 100/min, Enterprise TBD (Product).
- Over limit: 429 + Retry-After.
- Bad key: 401.
- Redis slow/down (50 ms): fail open, ratelimit_store_unavailable metric.
- X-RateLimit-Limit / X-RateLimit-Remaining headers.
