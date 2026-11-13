I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the function's docstring says so.

Before removing it I checked everything that consumes `load_readings`:

- `metrics/rollup.py` (`hourly_rollup`) carried a comment saying it relies on `load_readings` returning readings grouped by sensor and in time order. The code contradicts that: `hourly_rollup` sorts its own input by (sensor, time) before `groupby`. I corrected the comment to say the function sorts its own input and the caller's order does not matter. The sort there is kept.
- `alerts/spikes.py` (`find_spikes`) sorts by time itself, so it does not depend on input order.
- `cli/report.py` uses `hourly_rollup` and `find_spikes`, both of which sort internally, so its output is unchanged.
- `cli/export.py` already states that line order does not matter, and that is still true.
- `tests/test_readings.py` compares sorted values, so it does not depend on order.

Verification: `python -m unittest discover -s tests -t .` passes all 4 tests. A quick check confirmed that a file with the sensor order `t2, t1` now loads as `['t2', 't1']`.

Not verified: I did not profile the change, so the speedup on the large gateway files is unmeasured. I also did not add a test that pins file order; `tests/test_readings.py` has no test for it.
