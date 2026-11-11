I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

Nothing else depended on that order:
- `metrics/rollup.py` `hourly_rollup` already sorts by (sensor, time) before its `groupby`. Its comment claimed it relied on `load_readings` ordering, which was no longer true, so I reworded the comment to say it sorts itself.
- `alerts/spikes.py` `find_spikes` sorts by time itself.
- `cli/export.py` already states that line order does not matter.
- `cli/report.py` goes through the two functions above.

The unit tests pass (`tests/test_readings.py` and the discovered suite). I did not benchmark the change on the large gateway files, so the speedup from profiling is not measured here. The sort still runs once in `hourly_rollup`, so `cli/report.py` pays that cost in the rollup step.
