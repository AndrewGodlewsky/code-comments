send_alert now makes six attempts before it drops an alert, up from four.

Changes:
- `alerts/config.py`: `MAX_ATTEMPTS` is 6. The retry logic in `alerts/sender.py` reads it, so no logic change was needed.
- `alerts/sender.py`: updated the module docstring and the backoff comment. With six attempts the waits are 1, 2, 4, 8 and 16 s, so an alert is dropped about 31 s after the first try (it was about 7 s).
- `docs/oncall.md`: the drop time is now about 31 seconds, and the outage capacity figure is now 300 POSTs for a storm of 50 alerts (it was 200).

Verification: `python -m unittest` passes (3 tests). The existing tests derive their expectations from `MAX_ATTEMPTS`, so they pick up the new value. A manual run against a gateway that always returns 503 made 6 posts and waited [1, 2, 4, 8, 16] seconds before returning False.

Note: the longer retry window means an alert can take about 31 s to be dropped during an outage, where it used to take about 7 s. Anything that relies on the drop happening quickly will see that change.
