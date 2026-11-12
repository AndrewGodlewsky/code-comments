I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

Changes:

- `metrics/readings.py`: dropped the `readings.sort(...)` call. `load_readings` returns `[parse_line(...) ...]` directly. The docstring now reads "Return every reading in the file, in file order."
- `metrics/rollup.py`: the comment in `hourly_rollup` said it relied on `load_readings` returning readings grouped by sensor and in time order. That was no longer true once the sort moved out, and `hourly_rollup` already sorts its own input. I rewrote the comment to state the actual reason: `groupby` only groups adjacent items, so the readings must be sorted by sensor and time first.
- `alerts/spikes.py`: `find_spikes` sorted by `at` alone. Before this change, its input arrived sorted by `(sensor, at)`, so readings with the same timestamp came out in sensor-name order in `cli/report.py`'s `SPIKE` lines. Without the load sort that tie-break would have become file order. I changed the key to `(reading.at, reading.sensor)`, which gives the same `SPIKE` output as before. Spike detection itself does not depend on the tie order.

Checks:

- `python -m unittest discover -s tests -t .` passes (4 tests).
- On 2,000 random readings, `find_spikes` and `hourly_rollup` return the same results for the old input order and the new one.
- On 300,000 random synthetic lines, parsing took about 0.18 s and the sort about 0.37 s. The sort is a real cost, consistent with the profiling you described. I could not see your profile, so this is only a synthetic check.

Behaviour change to know about:

- `cli/export.py` now writes JSON lines in file order instead of sorted by sensor and time. Its own comment says line order does not matter because the dashboard indexes by sensor and time, so I left it alone. Confirm that the dashboard does not depend on the old order.

Not done: I did not commit or push anything, because this exercise said not to use git. There are no unrelated comments in the scope that I found to be false, and I left the existing comments in `cli/export.py` and the module docstring of `metrics/readings.py` unchanged.
