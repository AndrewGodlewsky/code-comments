send_alert now makes six attempts instead of four (`MAX_ATTEMPTS = 6` in `alerts/config.py`). With the existing doubling waits, an alert that keeps getting 502, 503 or 504 is dropped about 31 seconds after the first try (waits of 1, 2, 4, 8 and 16 s), instead of about 7 seconds.

Comments and docs that described the old numbers are corrected:
- `alerts/sender.py`: module docstring (six attempts) and the wait comment (1, 2, 4, 8, 16 s; about 31 s).
- `alerts/worker.py`: a 40-alert backlog in a full outage now takes about 21 minutes, not under five.
- `docs/oncall.md`: drop time about 31 seconds; a 50-alert storm sends at most 300 POSTs.
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times.

The unit tests pass (`python -m unittest`, 5 tests). The tests read `MAX_ATTEMPTS`, so they cover six attempts without edits.

Two things to check:
- Longer retries mean a full outage holds the worker much longer per alert. Each alert now waits about 31 seconds before it is dropped, so a large backlog during a long outage will take much longer to clear. If that matters, the cap or the base delay may need a second look.
- The request gives the goal (not losing pages in short gateway blips) but no reason for the specific number six. I did not record a rationale in any comment. If there is a ticket or incident behind the change, it should be added beside `MAX_ATTEMPTS`.
