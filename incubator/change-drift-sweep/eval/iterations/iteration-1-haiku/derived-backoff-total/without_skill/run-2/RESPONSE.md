send_alert now makes six attempts instead of four, so short gateway blips no longer drop alerts as quickly.

The change is one constant, `MAX_ATTEMPTS = 6` in `alerts/config.py`. The retry waits are derived from it, so they are now 1, 2, 4, 8 and 16 seconds, and an alert is dropped about 31 seconds after its first try (previously about 7 seconds).

I also updated the docs and comments that stated the old numbers:
- `alerts/sender.py`: module docstring and wait comment.
- `alerts/worker.py`: a 40-alert backlog in a full outage now takes about 21 minutes to clear, not under five.
- `docs/oncall.md`: drop time is about 31 seconds, and a storm of 50 alerts sends at most 300 POSTs, not 200.
- `docs/runbooks/gateway-maintenance.md`: the sender retries five times, not three. That line was already stale before this change, so it is corrected here too.

`python -m unittest` passes (5 tests). The tests read the constant, so they cover six attempts without edits.

Tradeoff: during a long outage, each alert holds the worker about 31 seconds and each drained alert sends up to six POSTs. Backlogs clear more slowly, and a gateway that is down for longer than about 30 seconds still loses alerts. Those alerts are logged as `alert_dropped`, as before.
