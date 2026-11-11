`send_alert` now tries six times: `MAX_ATTEMPTS` in `alerts/config.py` went from 4 to 6.
With the 1-second base delay doubling, the waits are 1, 2, 4, 8 and 16 seconds, so an
undeliverable alert is dropped about 31 seconds after the first try (it was about 7).

Updated every figure that came from the old count:
- the `alerts/sender.py` docstring (six attempts);
- the loop comment's waits and total;
- `docs/oncall.md`: the drop time, and the outage figure for a 50-alert storm, which is
  now at most 300 POSTs instead of 200;
- the `alerts/worker.py` docstring: in a full outage each alert holds the worker for about
  31 s, so a backlog of 40 now takes about 21 minutes to clear, not under five;
- the gateway-maintenance runbook, which said the sender retries three times; it now
  retries five times.

The 7-day outbox retention and the 503 note are unrelated and unchanged. The tests pass.
