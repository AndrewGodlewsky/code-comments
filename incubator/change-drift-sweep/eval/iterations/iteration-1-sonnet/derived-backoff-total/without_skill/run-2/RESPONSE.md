send_alert now makes six attempts before dropping an alert. The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`, and the unit tests pass.

With the doubling backoff, the waits are 1, 2, 4, 8 and 16 s. An alert is now dropped about 31 s after the first try, up from about 7 s.

Updated these places that described the old numbers:
- `alerts/sender.py`: the docstring now says six attempts, and the comment gives the new waits and the ~31 s total.
- `alerts/worker.py`: in a full outage, a backlog of 40 alerts now takes about 21 minutes to clear (40 x 31 s). It was under five minutes. The worker handles alerts one at a time, so a long outage will hold up the queue for much longer than before.
- `docs/oncall.md`: the drop time is now about 31 seconds, and a storm of 50 alerts sends at most 300 POSTs to the gateway, up from 200.
- `docs/runbooks/gateway-maintenance.md`: the sender now retries each alert five times, not three.

I did not change the backoff base or the retryable statuses. If the longer outage drain time is a problem, a cap on the wait or a smaller base delay would shorten it.
