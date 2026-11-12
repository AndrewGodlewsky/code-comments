I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

Before removing it I checked every caller for an order dependency:

- `metrics/rollup.py` had a comment saying it relies on `load_readings` returning readings sorted by sensor and time. That was stale: `hourly_rollup` sorts its own input before `groupby`, so it never depended on the loader's order. I replaced the comment with one stating the real reason for its sort (`groupby` only groups adjacent items).
- `alerts/spikes.py` sorts by `at` itself, so it is unaffected.
- `cli/report.py` sorts its output, and `cli/export.py` already states that line order does not matter.
- `tests/test_readings.py` sorts its own results.

`python -m unittest discover -s tests -t .` passes (4 tests). I did not profile the change, so the speed-up is not measured. I did not commit anything.
