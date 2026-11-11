I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so. I ran the tests and they pass, but they never check ordering, so I checked each caller by reading the code.

I grepped the whole repo for `load_readings`. It has three callers:
- `cli/export.py` doesn't need an order. Its comment says line order doesn't matter because the dashboard indexes by sensor and time.
- `cli/report.py` passes the readings to `hourly_rollup` and `find_spikes`, and both sort for themselves. `hourly_rollup` sorts by sensor and time. `find_spikes` sorts by time.
- `tests/test_readings.py` sorts the values itself before comparing.

One comment was stale. In `metrics/rollup.py`, a comment said `hourly_rollup` relied on `load_readings` returning sorted data. The code doesn't rely on that, because it sorts the readings itself, and `tests/test_rollup.py` confirms it accepts any order. I rewrote the comment to say that.

Nothing else depended on the sort. The remaining sort in `hourly_rollup` (and the one in `find_spikes`) is now the only one on the report path, so if the report is still slow on big files, that is the next place to look.
