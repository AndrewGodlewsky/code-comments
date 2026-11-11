send_alert now makes six attempts per alert instead of four. The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`, and the existing retry loop and backoff waits (1, 2, 4, 8, 16 s) pick it up.

With the doubling waits, an alert in a full outage is now dropped about 31 seconds after its first try, not 7. Because the worker sends alerts one at a time, a backlog of 40 alerts takes about 21 minutes to clear in an outage. I updated the comments and docs that stated the old numbers: the `send_alert` docstring and wait comment, the worker docstring, `docs/oncall.md` (drop time and the 50-alert POST count, now 300), and the gateway maintenance runbook (retries now five times).

The unit tests read `MAX_ATTEMPTS`, so they follow the new value. `python -m unittest` passes (5 tests).

Nothing is committed. Two things to check before you ship: the worker now holds for about 21 minutes per 40-alert backlog during an outage, which may matter if other alerts queue behind it, and the 31-second window is the sender's only retry budget, so a gateway outage longer than that still drops alerts.
