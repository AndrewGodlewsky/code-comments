send_alert now makes six attempts before giving up: MAX_ATTEMPTS in alerts/config.py went from 4 to 6. I did not run the tests.

The waits between attempts are now 1, 2, 4, 8 and 16 s, so a dropped alert is dropped about 31 s after it was raised (it was about 7 s). Every statement that depended on the old count is corrected:

- alerts/sender.py: the module docstring now says "at most six attempts", and the wait comment now says "1, 2, 4, 8 and 16 s ... about 31 s".
- alerts/worker.py: a backlog of 40 alerts in a full outage takes about 21 minutes (40 x 31 s), not "under five minutes".
- docs/oncall.md: "about 31 seconds" instead of seven, and a storm of 50 alerts sends at most 300 POSTs (50 x 6), not 200.
- docs/runbooks/gateway-maintenance.md: the sender retries each alert five times (six attempts), not three.

Left alone: OUTBOX_RETENTION_DAYS and "7 days" in docs/oncall.md, which is outbox retention and has nothing to do with the retry count. The tests use MAX_ATTEMPTS, so they follow the new value.

I found no mismatches that my change did not cause.

One thing to be aware of: a longer worst-case wait per alert means the worker blocks much longer in a full outage, as the 21-minute backlog figure shows.
