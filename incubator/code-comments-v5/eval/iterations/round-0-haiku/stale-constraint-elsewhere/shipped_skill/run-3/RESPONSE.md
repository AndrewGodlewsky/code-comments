I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so, with a note that callers needing sensor or time order must sort.

Changes:
- `metrics/readings.py`: dropped `readings.sort(...)`. Docstring now states file order.
- `metrics/rollup.py`: the comment above `hourly_rollup`'s sort said it relied on `load_readings` returning sorted data. That is no longer true, and `hourly_rollup` already sorts its own input. I rewrote the comment to give the real reason for its sort: `groupby` only groups adjacent items.

Tests: all 4 pass (`python -m unittest discover -s tests -t .`). I also checked by hand that `load_readings` returns lines in file order.

Things to check before calling the slowdown fixed:
- I did not time anything, so the speedup is unmeasured.
- `hourly_rollup` and `find_spikes` still sort internally. `cli/report.py` therefore still runs two sorts, so the profile will still show sorting. Only the sort in `load_readings` is gone.
- `find_spikes` sorts by time only. For readings from different sensors with the same timestamp, the order of printed SPIKE lines in `cli/report.py` may change. Spike detection itself is per sensor and is unaffected.
- `cli/export.py` now writes JSON lines in file order. Its existing comment already says line order does not matter, so I left it alone.

I did not commit or push, because git was out of scope for this task.
