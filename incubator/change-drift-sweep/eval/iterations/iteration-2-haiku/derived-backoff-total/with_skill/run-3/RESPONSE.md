send_alert now makes six attempts instead of four, so a short gateway blip no longer drops the alert.

Changes:
- `alerts/config.py`: `MAX_ATTEMPTS` is 6.
- The waits are now 1, 2, 4, 8 and 16 s, so an alert is dropped about 31 s after its first try (was about 7 s). The derived total is 1+2+4+8+16 = 31.

Prose I corrected to match the new values:
- `alerts/sender.py`: module docstring says six attempts; the wait comment gives the new waits and the 31 s drop time.
- `alerts/worker.py`: the backlog estimate is now under 21 minutes (40 alerts × 31 s = 1240 s). It was under five minutes (40 × 7 s = 280 s).
- `docs/oncall.md`: drop time is about thirty-one seconds; a 50-alert storm sends at most 300 POSTs (50 × 6), was 200.
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times (six attempts), was three.

Kept as written: no changelog, ADR or dated record mentions these values, and there are no outside facts or instruction-file lines affected. No drift predates this change.

Tests: `python -m unittest` passes (5 tests). The tests read `MAX_ATTEMPTS` and the wait sequence from the config, so they follow the new value. I did not add a test that pins six attempts specifically.

Trade-off to be aware of: during a full outage the worst case per alert grows from about 7 s to about 31 s, and the worker holds the outbox for longer while it drains. Alerts stuck behind a long outage will be delayed more.
