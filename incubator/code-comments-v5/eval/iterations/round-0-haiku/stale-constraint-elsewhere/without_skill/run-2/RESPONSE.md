I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order.

Nothing else needed the sort:
- `metrics/rollup.py` (`hourly_rollup`) sorts its own input before `groupby`, so its results are unchanged.
- `alerts/spikes.py` (`find_spikes`) sorts by time itself.
- `cli/export.py` says line order does not matter for the dashboard.

The comment in `metrics/rollup.py` said the function relied on `load_readings` returning readings grouped by sensor and in time order. That was already untrue, since the function sorts its input, so I rewrote the comment to say so.

The unit tests pass (4 of 4).

Caveat: `cli/report.py` still sorts, because `hourly_rollup` and `find_spikes` each sort. Running `report` therefore does not get faster by the full cost of the removed sort. Only `load_readings` callers, such as `export`, get the full saving. If the profile shows the remaining sorts dominating on large files, the next step is to sort once in the CLI and pass the sorted list to both functions, or to make the two functions accept pre-sorted input. I did not make that change because it would change their interfaces.
