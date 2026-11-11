I removed the sort from `load_readings` in `metrics/readings.py`. It now returns the readings in file order, and its docstring says so. The tests pass.

Before changing it I checked who else relies on the sorted order:

- **`metrics/rollup.py:11-12`**: a comment said `hourly_rollup` "relies on `load_readings` returning readings grouped by sensor and in time order". That comment was stale. The function sorts its own input on the next line, and `tests/test_rollup.py` checks that it accepts any order. I reworded the comment to say the sort happens there, because it would otherwise have been false after this change.
- **`alerts/spikes.py:10`**: `find_spikes` sorts by time itself, so it doesn't depend on the order either.
- **`cli/export.py:12`**: a comment says line order doesn't matter to the dashboard. That is still true, and I left it alone.
- **`cli/report.py`**: it passes the readings straight to `hourly_rollup` and `find_spikes`, which both sort for themselves.

`hourly_rollup` and `find_spikes` still sort on every call, which is the same cost as before. If the report on a big file is still slow, that is the next place to look.
