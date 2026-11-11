`send_alert` now makes six attempts instead of four (`MAX_ATTEMPTS = 6` in `alerts/config.py`). That gives five retry waits of 1, 2, 4, 8 and 16 seconds, so an alert is dropped about 31 seconds after the first try, up from about 7 seconds. The existing test suite passes (`python -m unittest`, 5 tests).

I also corrected the text that the change made stale:

- `alerts/sender.py`: the module docstring says six attempts, and the wait comment now lists 1, 2, 4, 8 and 16 s and the 31 s drop time.
- `alerts/worker.py`: a 40-alert outage backlog now takes under twenty-one minutes to clear (40 x 31 s), not under five minutes.
- `docs/oncall.md`: the drop time is about 31 seconds, and a 50-alert storm sends at most 300 POSTs (50 x 6), not 200.
- `docs/runbooks/gateway-maintenance.md`: during a drain the sender retries each alert five times, not three.

Mismatches I found that my change did not cause: none. The 7-day outbox retention in `docs/oncall.md` and `alerts/config.py` agree with each other, and the tests derive their expected values from `MAX_ATTEMPTS` and `BASE_DELAY_S`, so they needed no edits.
