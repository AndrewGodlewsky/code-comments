I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order. The unit tests pass (4 of 4).

Constraint sweep, before the edit:

- `metrics/rollup.py:11-12` said `hourly_rollup` relies on `load_readings` returning readings grouped by sensor and in time order. The function already re-sorts its input at line 13, so that reliance was stale. Removing the sort would have made the comment false, so I rewrote it to say that `hourly_rollup` sorts here instead of relying on the caller's order. Nothing else changed in that file.
- `cli/export.py:12` says line order does not matter because the dashboard indexes by sensor and time. This is consistent with the change, so I left it alone. Export output now follows file order instead of sensor-then-time order.
- `alerts/spikes.py` sorts by `at` itself, `cli/report.py` relies on `hourly_rollup` and `find_spikes` for ordering, and `tests/test_rollup.py` already exercises any-order input. None of these depend on `load_readings` order.
- No live constraint was found, so nothing had to be kept.

Behaviour changes to be aware of:

- `SPIKE` lines from `cli/report.py` can come out in a different order when two sensors spike at the same timestamp. `find_spikes` sorts by timestamp only, so ties now follow file order instead of sensor name.
- Rollup means for two readings of the same sensor at the same timestamp may differ in the last floating-point bits, because the summation order can change.

Files changed: `metrics/readings.py` (sort removed) and `metrics/rollup.py` (comment corrected).
