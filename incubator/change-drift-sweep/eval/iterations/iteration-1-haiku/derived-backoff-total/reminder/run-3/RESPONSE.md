send_alert now makes six attempts instead of four, so alerts survive short gateway blips.

Changes:
- alerts/config.py: MAX_ATTEMPTS 4 -> 6. The waits stay at 1, 2, 4, 8 and 16 s, so an alert is now dropped about 31 s after the first try, not about 7 s.
- alerts/sender.py: the module docstring says six attempts, and the wait comment gives the new schedule and the 31 s figure.
- alerts/worker.py: a backlog of 40 alerts in a full outage now takes about 21 minutes to clear, not under five minutes.
- docs/oncall.md: the drop time is about 31 seconds, and a storm of 50 alerts sends at most 300 POSTs, not 200.
- docs/runbooks/gateway-maintenance.md: the sender retries each alert five times, not three.

Left alone: the 7-day outbox retention in docs/oncall.md and OUTBOX_RETENTION_DAYS, which are unrelated to retries.

No mismatches existed before this change that I did not cause. The tests pass (python -m unittest, 5 tests) and derive their expectations from MAX_ATTEMPTS, so they needed no edits.

Trade-off to be aware of: in a full outage each alert now holds the worker for about 31 s instead of about 7 s, so a backlog clears more slowly.
