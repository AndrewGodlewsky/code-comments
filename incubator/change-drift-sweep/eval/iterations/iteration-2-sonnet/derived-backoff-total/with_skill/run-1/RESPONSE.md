send_alert now makes six attempts instead of four. `MAX_ATTEMPTS` in `alerts/config.py` is 6, and the tests pass. Five waits of 1, 2, 4, 8 and 16 s now separate the attempts, so a dropped alert is dropped about 31 s after the first try, up from about 7 s.

Prose corrected to match, by file:
- `alerts/sender.py`: the module docstring now says "six attempts". The wait comment now reads "Waits of 1, 2, 4, 8 and 16 s ... about 31 s".
- `alerts/worker.py`: the backlog estimate for 40 alerts in a full outage was "under five minutes". It is now "about 21 minutes" (40 x 31 s = 1240 s).
- `docs/oncall.md`: the drop time is now "about 31 seconds" (was seven). A storm of 50 alerts now sends at most 300 POSTs (was 200).
- `docs/runbooks/gateway-maintenance.md`: the sender "retries each alert five times" (was three). That is six attempts, so five retries.

Kept as written:
- `OUTBOX_RETENTION_DAYS = 7` and "7 days" in `docs/oncall.md` are the outbox retention, not the old wait total.

I changed no code beyond the constant. The retry loop, waits and tests all derive from `MAX_ATTEMPTS`. No changelog, ADR or instruction file mentions the old value, and I found no drift that predates this change.

Longer retries mean the worker takes longer to clear a backlog during a full outage. At about 31 s per alert, 40 alerts hold it for roughly 21 minutes.
