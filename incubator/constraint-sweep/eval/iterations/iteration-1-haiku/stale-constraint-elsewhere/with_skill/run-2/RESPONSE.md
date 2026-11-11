I removed the sort from `load_readings` in `metrics/readings.py` (the `readings.sort(...)` line before the return). The file now returns readings in file order. The unit tests pass (4 of 4). I did not profile, so I have not measured the speedup.

Constraint sweep:

- `metrics/rollup.py:11-12` says `hourly_rollup` relies on `load_readings` returning readings grouped by sensor and in time order. This is now stale. `hourly_rollup` sorts its own input at line 13, so it establishes the order itself and does not depend on the loader. I left the comment unchanged because the wording fix belongs to the code-comments skill. That comment is now false and should be reworded or removed.
- `alerts/spikes.py:10` sorts by time itself and tracks state per sensor, so it does not depend on load order.
- `cli/export.py:12` says line order does not matter. No change needed.
- `cli/report.py` passes the readings to `hourly_rollup` and `find_spikes`, which both sort their own input. The rollup output is sorted at print time. One observable change: `SPIKE` lines for different sensors at the identical timestamp may now print in file order rather than sensor order. No stated constraint or test covers this.
- `tests/test_readings.py` compares with `sorted(...)`, and no test pins the loader's order.
