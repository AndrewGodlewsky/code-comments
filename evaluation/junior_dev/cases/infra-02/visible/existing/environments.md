# shop-api environments (as of today)

## CI today
- The CI runner runs on pull requests only: build the image, then unit tests
  (`make test-unit`, about 4 min). Nothing is pushed and nothing is deployed.
- Integration tests (`make test-integration`, about 12 min, needs a Postgres
  service container) are only run by hand. One test is known to be flaky.
- CI may push to `registry.internal/shop-api` and has credentials to run
  `deploy.sh` against both clusters.
- CI supports manual approval jobs restricted to a group (it records who
  approved and when), and named locks that only one run can hold at a time.

## Staging
- Kubernetes context `staging`, namespace `shop`. Own Postgres. Internal only.
- Smoke tests: `make smoke ENV=staging` (about 3 min, hits the staging URL).

## Production
- Kubernetes context `production`, namespace `shop`.
- `shop-api` is the stable deployment.
- `shop-api-canary` is a second deployment that normally has 0 replicas.
  While it has ready pods, the load balancer sends it 10% of traffic.
- Stable and canary share the production Postgres.
- Metrics are in Prometheus. Canary 5xx ratio over the last minute:

      sum(rate(http_requests_total{app="shop-api-canary",code=~"5.."}[1m]))
      / sum(rate(http_requests_total{app="shop-api-canary"}[1m]))

## Release policy
- Deployment window: a production deploy may START Monday to Thursday,
  09:00 to 15:00 UTC. Once started it may finish after 15:00.
- Approvers: the `release-approvers` group in the CI system.
- Announcements: Slack channel #deploys.
