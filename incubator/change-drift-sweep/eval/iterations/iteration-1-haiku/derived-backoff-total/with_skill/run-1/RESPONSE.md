`send_alert` now makes six attempts instead of four, so an alert survives a short gateway blip.

The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`. The waits stay doubling, so there are five of them, 1, 2, 4, 8 and 16 seconds, and an alert is now dropped about 31 seconds after the first try (it was about 7 seconds). The unit tests pass (`python -m unittest`).

Prose that stated the old figures, now corrected:
- `alerts/sender.py`: module docstring says "at most six attempts"; the wait comment gives 1, 2, 4, 8 and 16 s and about 31 s.
- `alerts/worker.py`: a backlog of 40 alerts in a full outage now takes over twenty minutes to clear (40 x 31 s = 1240 s), not under five minutes.
- `docs/oncall.md`: a dropped alert is about thirty-one seconds old, not seven; a storm of 50 alerts sends at most 300 POSTs, not 200.
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times, not three.

Kept as written: the "7 days" outbox retention in `docs/oncall.md` and `OUTBOX_RETENTION_DAYS` (a different setting, unrelated to the retry count), and the step number "3." in the runbook.

Consequence to know about: during planned drains, each alert now holds the worker for up to 31 seconds, so a large backlog takes much longer to clear. No ADR was affected. The repository has no changelog file, so no changelog line was added.
