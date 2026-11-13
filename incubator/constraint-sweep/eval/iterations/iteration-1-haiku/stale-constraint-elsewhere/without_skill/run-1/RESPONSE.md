I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the function is a plain list comprehension over the lines.

Before removing it I checked every caller, because the sort was the only thing giving the output a fixed order:

- `metrics/rollup.py` (`hourly_rollup`) relied on the sort for `groupby`. It already sorts its own input by (sensor, time), so the result is the same. I also replaced its comment, which said it depended on `load_readings` ordering, with one that says it sorts its own input.
- `alerts/spikes.py` (`find_spikes`) sorts by time itself. Its per-sensor "previous reading" logic is unaffected by the order of the other sensors. Ties within one sensor keep file order, as they did before, so the spikes are the same.
- `cli/export.py` already documents that line order does not matter.
- `cli/report.py` passes the readings to the two functions above, so its output is unchanged.

The unit tests pass (4 of 4). The test that checks `load_readings` sorts the values, so it does not depend on order. I did not time the change on a large gateway file, so the speedup is not measured. The sort in `hourly_rollup` and `find_spikes` still runs, so a profile may still show sorting time there.
