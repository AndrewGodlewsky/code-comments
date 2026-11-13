I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

I checked every caller first:
- `metrics/rollup.py` (`hourly_rollup`) already sorts its own input. Its comment said it relied on `load_readings` for the ordering, which was stale, so I reworded it.
- `alerts/spikes.py` (`find_spikes`) already sorts by time itself.
- `cli/export.py` doesn't depend on order, and its comment says so.
- `cli/report.py` only passes the readings on to the two functions above.

Tests pass. Both `hourly_rollup` and `find_spikes` still sort internally. If the rollup is also slow on big files, that sort is the next place to look, but I didn't touch it.
