send_alert now makes six attempts instead of four. The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`, so the retry waits are now 1, 2, 4, 8 and 16 s and an alert is dropped about 31 s after the first try (previously about 7 s). The unit tests pass (`python -m unittest`, 5 tests).

I also corrected the statements that the new numbers made false:
- `alerts/sender.py`: module docstring (six attempts) and the wait comment (31 s).
- `alerts/worker.py`: a 40-alert outage backlog now takes about twenty minutes to clear, not under five.
- `docs/oncall.md`: drop time is about 31 s, and a 50-alert storm sends at most 300 POSTs.
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times during a drain.

Please note that this roughly quadruples how long a full outage holds the worker, and a dropped alert now takes about 31 s to surface. Confirm that the on-call lead is comfortable with that trade-off.
