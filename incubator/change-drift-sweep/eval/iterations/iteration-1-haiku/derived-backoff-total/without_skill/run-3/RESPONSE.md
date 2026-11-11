I raised the send_alert retry limit from four attempts to six, so a short gateway blip no longer drops the alert.

What changed:
- `alerts/config.py`: `MAX_ATTEMPTS` is now 6. The retry waits double, so an alert now waits 1, 2, 4, 8 and 16 seconds between attempts and is dropped about 31 seconds after the first try (it was about 7 seconds).
- `alerts/sender.py`: the module docstring and the inline comment now say six attempts and the 31-second window.
- `alerts/worker.py`: a backlog of 40 alerts in a full outage now takes about twenty minutes to clear, not under five.
- `docs/oncall.md`: the drop window is 31 seconds and a storm of 50 alerts sends at most 300 POSTs (was 200).
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times during a drain (was three).

Verification: `python -m unittest` runs 5 tests and all pass. The tests read `MAX_ATTEMPTS` from config, so they follow the new limit without edits.

Things to be aware of:
- Alerts that hit a full outage now hold the worker about 31 seconds each, so a large backlog stays blocked longer. Drops are still logged as `alert_dropped`.
- The retry count is a constant with no test that pins the literal value of 6. If you want that guarded, a one-line assertion would do it.
