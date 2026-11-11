send_alert now makes six attempts before it drops an alert, up from four. The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`. The waits are 1, 2, 4, 8 and 16 seconds, so an alert is dropped about 31 seconds after its first try, up from about 7 seconds.

Side effects I updated in the same change:

- `alerts/sender.py`: the module docstring and the wait comment now say six attempts and 31 seconds.
- `alerts/worker.py`: the docstring said a backlog of 40 alerts clears in under five minutes during an outage. At 31 seconds per alert that is about 21 minutes, so I changed the figure.
- `docs/oncall.md`: the drop time is now about 31 seconds, and a storm of 50 alerts sends at most 300 POSTs, up from 200.
- `docs/runbooks/gateway-maintenance.md`: the sender now retries each alert five times, up from three.

The unit tests pass (`python -m unittest`, 5 tests). They read `MAX_ATTEMPTS` from config, so they now check six attempts and the longer wait sequence without edits. I did not add a new test for the number 6 itself.

Trade-off: during a long gateway outage, each alert holds the worker for about 31 seconds instead of 7. A backlog drains about four times more slowly. That is the cost of riding out short blips. Alerts that fail every attempt are still logged as `alert_dropped`.
