I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so. I haven't run the tests or timed it on a big gateway file.

I checked every caller before removing it, since the old code returned readings sorted by sensor and time:

- `hourly_rollup` in `metrics/rollup.py` already sorts its input itself, so its results don't change. Its comment said it relied on `load_readings` for the order, which was out of date, so I corrected it. That sort in `hourly_rollup` is still O(n log n), so `cli/report.py` will still pay for a sort. Only the duplicate one in the load path is gone. If you want the rollup faster too, it could group in a dict instead of sorting.
- `find_spikes` in `alerts/spikes.py` sorts by time itself.
- `cli/export.py` says line order doesn't matter, so its output is unaffected apart from line order.
- The test in `tests/test_readings.py` sorts the values before comparing.

The only visible change is that `cli.export` now writes lines in file order instead of sorted order.
