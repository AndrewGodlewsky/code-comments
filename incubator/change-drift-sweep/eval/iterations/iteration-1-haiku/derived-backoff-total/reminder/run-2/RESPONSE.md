`send_alert` now makes six attempts before it drops an alert, up from four. `MAX_ATTEMPTS` in `alerts/config.py` is 6, so the retry waits are now 1, 2, 4, 8 and 16 seconds.

Figures that followed from the old value and are now corrected:

- `alerts/sender.py`: the module docstring says six attempts, and the wait comment gives 1, 2, 4, 8 and 16 s and a drop about 31 s after the first try (was 7 s).
- `alerts/worker.py`: a backlog of 40 alerts in a full outage now takes under 21 minutes to clear (was under five minutes, which was 40 × 7 s).
- `docs/oncall.md`: an alert is dropped about 31 seconds after it is raised (was about seven). A storm of 50 alerts sends at most 300 POSTs (was 200).
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times during a drain (was three).

Left unchanged on purpose:

- `OUTBOX_RETENTION_DAYS = 7` and the "7 days" line in `docs/oncall.md` concern outbox purging, not retries.
- The tests in `tests/test_sender.py` use `MAX_ATTEMPTS` and contain no hard-coded attempt counts, so they needed no edits. `python -m unittest` passes (5 tests).

I found no mismatches that predate this change.
