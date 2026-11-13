I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order. The four unit tests pass, and `cli.report` still prints the same rollup on an out-of-order file.

Sweep results:
- `metrics/rollup.py:11-12` said `hourly_rollup` relies on `load_readings` returning readings grouped by sensor and in time order. That was stale: `hourly_rollup` already sorts its own input before `groupby`, so it does not depend on the loader. I did not block on it. Because the comment described the ordering I removed, I reworded it to say that `groupby` needs adjacent items and that the function sorts before grouping.
- `cli/export.py:12` says line order does not matter, and `alerts/spikes.py` sorts its own input. Neither depends on the loader's order, so I left them alone.
- `cli/report.py` and `tests/test_readings.py` do not depend on the order. The test sorts the values itself.
- No live constraint was found, so nothing needed keeping or reporting as broken.

Not done: `hourly_rollup` still sorts the full list, so `cli.report` sorts the readings twice. The load-time sort was the only one you asked me to remove. If the rollup sort is also a cost, it is a separate change.
