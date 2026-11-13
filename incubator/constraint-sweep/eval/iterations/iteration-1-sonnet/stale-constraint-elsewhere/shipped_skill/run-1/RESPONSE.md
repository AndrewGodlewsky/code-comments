I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

I checked every caller before removing it:
- `hourly_rollup` sorts its own input. Its old comment said it relied on `load_readings` returning sorted data, which was false, so I corrected it to say why it sorts.
- `find_spikes` sorts by time itself.
- `cli/export.py` doesn't depend on order, because the dashboard indexes by sensor and time.

I did not run the tests or time it on a big file. The sort that matters for the slowdown is gone, but `hourly_rollup` and `find_spikes` still sort on their own, so `cli/report.py` still sorts the data twice. If that is slow too, those would be the next place to look.
