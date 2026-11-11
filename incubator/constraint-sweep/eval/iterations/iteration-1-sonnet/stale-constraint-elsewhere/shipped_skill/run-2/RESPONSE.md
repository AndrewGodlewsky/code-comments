I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order.

I didn't run the tests, and I didn't time it on a large gateway file.

I checked each caller that might have depended on the ordering:
- `hourly_rollup` already sorts its input itself, so it still works.
- `find_spikes` sorts by time itself.
- `cli/export.py` says line order doesn't matter, because the dashboard indexes by sensor and time.
- `test_load_returns_every_reading` sorts the values before comparing.

Comment fixes:
- The `load_readings` docstring now says the result is in file order, not sorted.
- The comment in `hourly_rollup` said it relied on `load_readings` returning sorted readings. That was false now, and arguably already false because the function sorts anyway. It now says the sort is there because `groupby` only groups adjacent items and `load_readings` doesn't order its result.

`hourly_rollup` and `find_spikes` each still sort the readings. `hourly_rollup` sorts the whole list again, so `report` still pays for sorting on big files. If that is the slow part, removing those sorts needs a separate decision.
