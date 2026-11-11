send_alert now makes six attempts instead of four, so a short gateway blip no longer drops the alert.

Changes:
- `alerts/config.py`: `MAX_ATTEMPTS` is 6. The waits stay at 1, 2, 4, 8 and 16 s, so an alert is dropped about 31 s after its first try (was 7 s).
- `alerts/sender.py`: the module docstring says six attempts, and the wait comment gives the new waits and the 31 s drop time.
- `alerts/worker.py`: the docstring said a backlog of 40 alerts clears in under five minutes. In a full outage that is now 40 x 31 s = 1,240 s, about 21 minutes, so I corrected it.
- `docs/oncall.md`: the drop time is now about 31 seconds. A storm of 50 alerts in a full outage now sends at most 300 POSTs (50 x 6), not 200.
- `docs/runbooks/gateway-maintenance.md`: the sender now retries each alert five times, not three.

Kept as written:
- `OUTBOX_RETENTION_DAYS = 7` and the "7 days" line in `docs/oncall.md`. They describe outbox retention, not retries, and the value did not change.

Verification: `python -m unittest` passes (5 tests). The drift script finds no remaining prose that states the old attempt count, drop time, POST count or drain time. The tests read `MAX_ATTEMPTS` rather than a literal, so they needed no edits.

Nothing was committed, and no git or task tracking was used, as the task required.
