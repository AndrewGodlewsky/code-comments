# Public API contract (excerpt)

## 4. Rate limits

Limits apply per client API key.

- A client may send a burst of up to **20 requests**.
- Sustained throughput is **5 requests per second**.
- A request over the limit receives `429 Too Many Requests` with a
  `Retry-After` header giving the number of seconds to wait.

Newly started gateway instances must accept a full burst immediately; the load
balancer health-checks new instances in a burst as soon as they register.
