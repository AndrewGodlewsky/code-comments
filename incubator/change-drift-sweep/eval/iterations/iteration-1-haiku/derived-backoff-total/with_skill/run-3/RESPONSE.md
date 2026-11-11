I changed `MAX_ATTEMPTS` from 4 to 6 in `alerts/config.py`, so `send_alert` now makes six attempts before it drops an alert. The waits are 1, 2, 4, 8 and 16 seconds, so an alert is dropped about 31 seconds after the first try (it was about 7 seconds). The unit tests pass.

I also corrected the prose that stated the old values:
- `alerts/sender.py`: the module docstring says six attempts, and the wait comment lists the new waits and the 31-second drop time.
- `alerts/worker.py`: a 40-alert backlog in a full outage now takes about 21 minutes to clear (40 × 31 s), not under five minutes.
- `docs/oncall.md`: the drop time is about thirty-one seconds, and a 50-alert storm sends at most 300 POSTs (50 × 6), not 200.
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times, not three.

Kept as written: the `OUTBOX_RETENTION_DAYS = 7` setting and the "7 days" outbox line in `docs/oncall.md`. They describe outbox retention, not retries, so they are unrelated to this change. No records, outside facts or instruction files were affected. `README.md` and the tests needed no edits; the tests read `MAX_ATTEMPTS` from config.
