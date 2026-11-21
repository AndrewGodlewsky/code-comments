## Per-customer rate limiting on the public API

We're adding rate limiting to the public REST API so that one noisy customer can't degrade service for everyone else. Please write the design as a **Mermaid `sequenceDiagram`, with short notes before or after it**, for anything the diagram can't show on its own.

### Existing system

- All public traffic goes through the API Gateway. It runs as 6 stateless instances behind a load balancer, and any instance can receive any request.
- Clients send an API key in the `X-Api-Key` header. The gateway already calls the Key Service to resolve the key to a customer ID and a plan (Standard or Enterprise). It caches that answer in memory for 5 minutes.
- The gateway then forwards the request to the backend service that owns the route and passes the backend's response back.

### Fixed requirements

1. Limits are per customer, not per key. A customer with several keys has one budget shared by all of them.
2. Standard customers get 100 requests per minute. Product has not decided the Enterprise limit yet. Don't pick a number; leave it visibly open.
3. Authentication comes first. A request with a missing or unknown key gets `401` and must not read or change any rate-limit counter.
4. The rate-limit check runs after authentication and before forwarding. A request over the limit gets `429 Too Many Requests` with a `Retry-After` header (in seconds) and is never forwarded. Requests rejected with 429 do not use up budget.
5. A request that passes the check counts against the budget even if the backend then fails (for example, returns 500).
6. Responses to requests that passed the check carry `X-RateLimit-Limit` and `X-RateLimit-Remaining`.
7. Counts must be shared across all gateway instances. Spreading a customer's traffic over 6 instances must not give them 6x their limit.
8. If the counter store errors or doesn't answer within 50 ms, fail open: forward the request anyway and emit a `ratelimit_store_unavailable` metric. A counter outage must not take the API down.

### Your call

You decide which store holds the counters, how the one-minute window behaves, how concurrent requests on different instances are kept from overshooting, how `Retry-After` is worked out, and what a fail-open response looks like. Keep it simple: this is a first version.
