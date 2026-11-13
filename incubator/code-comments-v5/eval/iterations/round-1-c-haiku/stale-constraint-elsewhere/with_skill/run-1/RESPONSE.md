I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

I checked each consumer before removing it:
- `metrics/rollup.py` `hourly_rollup` sorts its own input by (sensor, time) before `groupby`, so it never depended on the load-time sort. Its comment said it relied on `load_readings` order. That was already false, so I replaced it with a comment saying `groupby` needs adjacent items and that input order is not assumed.
- `alerts/spikes.py` `find_spikes` sorts by time itself. Its output is unchanged, because same-sensor ties keep file order either way.
- `cli/report.py` sorts its rollup output before printing, so its output is unchanged.
- `cli/export.py` already states that line order does not matter. Its output rows now follow file order.

The unit tests pass (4 tests, run with `python -m unittest discover -s tests -t .`). I did not profile the change, so I have not measured the speedup. The `report` path still sorts twice, once in `hourly_rollup` and once in `find_spikes`, so it saves one of three sorts, not all of them.
