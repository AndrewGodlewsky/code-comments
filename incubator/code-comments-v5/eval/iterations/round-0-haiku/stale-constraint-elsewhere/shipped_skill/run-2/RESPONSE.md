I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

Every caller that needs an order sorts for itself, so nothing else changes:
- `metrics/rollup.py` sorts by sensor and time before grouping. Its comment claimed it relied on `load_readings` returning grouped, time-ordered readings, which was already untrue and would now be plainly false. I rewrote it to say the rollup sorts because `groupby` only groups adjacent items and readings arrive in file order.
- `alerts/spikes.py` sorts by time itself.
- `cli/export.py` already notes that line order does not matter.
- `cli/report.py` only passes the readings through to the rollup and spikes.

The test suite passes (4 tests, run with `python -m unittest discover -s tests -t .`). I did not benchmark the change, so I have not confirmed the speedup. Parsing every line may still dominate the load time on the big gateway files.

I did not add a test for the new file-order behaviour. The existing tests already cover both callers' order handling.
