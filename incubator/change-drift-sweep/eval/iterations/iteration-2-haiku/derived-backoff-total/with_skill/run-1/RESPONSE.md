I changed `MAX_ATTEMPTS` in `alerts/config.py` from 4 to 6, so `send_alert` now makes six attempts before it drops an alert. The waits stay doubling from 1 s, which makes five waits (1, 2, 4, 8, 16 s). The unit tests pass (`python -m unittest`, 5 tests).

I also updated the prose that stated the old figures:

- `alerts/sender.py`: the module docstring now says six attempts, and the wait comment says the alert is dropped about 31 s after the first try (1+2+4+8+16 = 31; it was about 7 s).
- `alerts/worker.py`: a backlog of 40 alerts in a full outage now takes about 21 minutes to clear (40 × 31 s = 1,240 s ≈ 20.7 min; it was "under five minutes").
- `docs/oncall.md`: the drop time is now about 31 seconds, and a storm of 50 alerts sends at most 300 POSTs (50 × 6; it was 200).
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times (six attempts is one try plus five retries; it said three).

Nothing else needed changing. The tests read `MAX_ATTEMPTS` rather than a literal, and the README does not state the figures. The outbox retention of 7 days is unrelated to the retry count, so I left it alone.

Keep in mind that the 21-minute and 31-second figures count only the waits, not the time each POST takes to fail, so the real times will be a little longer. Also, a planned drain now holds each alert for about 31 s rather than 7 s, so the outbox will back up for longer during a maintenance window.
