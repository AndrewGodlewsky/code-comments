send_alert now makes up to six attempts (`MAX_ATTEMPTS = 6` in `alerts/config.py`) before dropping an alert. Waits double from 1 s: 1, 2, 4, 8, 16, so a dropped alert is given up on about 31 s after the first try (was about 7 s). I did not run the tests. They are written against `MAX_ATTEMPTS`, so they should follow the new value.

Comments and docs that stated the old behaviour, now corrected:
- `alerts/sender.py`: module docstring (six attempts) and the wait comment (1, 2, 4, 8, 16 s; about 31 s).
- `alerts/worker.py`: the backlog estimate. 40 alerts in a full outage now take about 21 minutes (40 x 31 s), not under five.
- `docs/oncall.md`: drop time (about 31 s) and the storm bound (50 alerts send at most 300 POSTs, was 200).
- `docs/runbooks/gateway-maintenance.md`: the sender retries five times (was three).

Things to be aware of:
- The longer worker hold-up is the main cost. During a full outage the worker is blocked about 31 s per alert, so later alerts in the outbox wait much longer. Alerts are also sent oldest first, one at a time, so a long backlog delays fresh pages. Decide whether that is acceptable.
- The gateway sees up to 50% more POSTs during an outage (300 instead of 200 for a 50-alert storm). If the gateway has a rate limit, check it.
- No one gave a reason for choosing six, so the comments record only the value. If there is a reason (for example, how long the blips last), tell me and I can note it next to `MAX_ATTEMPTS`.
