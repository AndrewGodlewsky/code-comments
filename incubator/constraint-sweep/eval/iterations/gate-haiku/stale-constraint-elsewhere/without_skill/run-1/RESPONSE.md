I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

I checked the callers before removing it. `hourly_rollup` in `metrics/rollup.py` and `find_spikes` in `alerts/spikes.py` both sort their own input, so `cli/report.py` gives the same output as before. `cli/export.py` already documents that line order does not matter. The tests compare sorted values or pass readings in shuffled order, so they still pass (4 of 4).

The comment in `metrics/rollup.py` said `hourly_rollup` relied on `load_readings` returning readings grouped by sensor and in time order. That was no longer true once the sort was gone, so I rewrote it to say the function sorts its own input.

I left the sort inside `hourly_rollup` in place. It is now the only sort on the report path, so it is the place to look if the rollup is still slow on large files. Removing it would mean `hourly_rollup` silently depends on callers pre-sorting, so I did not change it as part of this request.
