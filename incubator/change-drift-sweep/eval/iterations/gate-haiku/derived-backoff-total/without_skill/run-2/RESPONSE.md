`send_alert` now makes six attempts instead of four before it drops an alert. The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`.

The retry waits double, so the alert is now dropped about 31 seconds after the first try (1, 2, 4, 8 and 16 seconds between attempts), not about 7. I updated the sender docstring and comment, and `docs/oncall.md` for the new timing and for the outage capacity: 50 alerts now send at most 300 POSTs during a full outage, not 200. The existing tests read `MAX_ATTEMPTS`, and all three pass with `python -m unittest`.

Nothing was committed.
