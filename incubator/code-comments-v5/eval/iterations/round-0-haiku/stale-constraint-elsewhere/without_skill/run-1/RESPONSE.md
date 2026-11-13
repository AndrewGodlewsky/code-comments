I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

I checked each caller before removing it:

- `metrics/rollup.py` `hourly_rollup` already sorts its own input by (sensor, time) before `groupby`, so its results do not change.
- `alerts/spikes.py` `find_spikes` sorts by time itself.
- `cli/export.py` already notes that line order does not matter.
- `cli/report.py` only uses the rollup and spike outputs, which are unaffected.

The comment in `metrics/rollup.py` said `hourly_rollup` relied on `load_readings` ordering. That was no longer true, so I rewrote it to say the function sorts its own input.

Tests: `python -m unittest discover -s tests -t .` runs 4 tests, all passing.

I did not change the sort in `hourly_rollup` or in `find_spikes`. Those are the only sorts left on this path, and they are needed for correct results on unordered input. I have not profiled the big gateway files, so the speedup is not measured.
