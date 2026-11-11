I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

I checked every caller first, because the sort looked like it might be load-bearing:
- `metrics/rollup.py` (`hourly_rollup`) has a comment saying it relies on `load_readings` returning sorted data. That comment was stale: the function already sorts its input itself, so results are unchanged. I updated the comment to match.
- `alerts/spikes.py` (`find_spikes`) sorts by time itself, so it is unaffected.
- `cli/export.py` does not depend on order, as its own comment says.
- `cli/report.py` passes the readings to the two functions above, so it is unaffected.

The existing tests pass. The one thing I did not do is remove the sorts inside `hourly_rollup` and `find_spikes`. They are still O(n log n) on each report run, so if profiling later points at them, they are the next place to look. The sort in `hourly_rollup` is needed unless you guarantee sorted input.
