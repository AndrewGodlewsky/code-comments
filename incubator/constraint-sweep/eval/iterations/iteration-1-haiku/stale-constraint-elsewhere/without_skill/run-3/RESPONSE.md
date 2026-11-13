I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the function no longer does an O(n log n) sort over the whole file.

Before removing it I checked every caller:

- `metrics/rollup.py` `hourly_rollup` already sorts its input itself, because `groupby` only groups adjacent items. Its comment claimed it relied on `load_readings` ordering, which was already untrue. I rewrote that comment to say the sort lives in `hourly_rollup` and `load_readings` does not order its output.
- `alerts/spikes.py` `find_spikes` sorts by timestamp itself.
- `cli/export.py` states that line order does not matter.
- `cli/report.py` passes the readings to `hourly_rollup` and `find_spikes`, so it is covered by the two points above.
- `tests/test_readings.py` already compares sorted values.

The unit tests pass (4 tests, `python -m unittest`).

Caveat: `hourly_rollup` still sorts the whole list, so `cli/report.py` pays the sort cost once in the rollup. If the profile is dominated by that sort rather than by `load_readings`, the rollup sort is the next candidate. I did not time the change on a large gateway file, so the speedup is not measured.
