# On-call alerting

Alerts go to the paging gateway.
If the gateway is down or draining, the sender retries with doubling waits and drops the alert about 31 seconds after it was raised.
Each drop is logged as `alert_dropped`; check the log before assuming an alert was never raised.

## Capacity

In a full outage every alert uses all its attempts, so a storm of 50 alerts sends at most 300 POSTs to the gateway before the sender gives up.

## Outbox

Undelivered alerts stay in the outbox for 7 days, then they are purged.
