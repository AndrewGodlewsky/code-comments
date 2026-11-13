I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

Nothing else in the code depended on that sort:
- `metrics/rollup.py` (`hourly_rollup`) sorts its own input before `groupby`. Its comment claimed it relied on `load_readings` order, which was no longer true. I rewrote the comment to say the function sorts because `groupby` only groups adjacent items, and that `load_readings` returns file order.
- `alerts/spikes.py` (`find_spikes`) already sorts by time itself.
- `cli/export.py` already states that line order does not matter.
- `cli/report.py` sorts the rollup output before printing.
- `tests/test_readings.py` compares sorted values, and `tests/test_rollup.py` covers out-of-order input.

The unit tests pass (4 tests, `python -m unittest`).

Two things to check:
1. The sort has not gone away for the rollup path. `hourly_rollup` still sorts all readings, and `find_spikes` sorts again, so `cli/report.py` still sorts twice. If the slowdown is in `report`, you will see less gain than you expect. I did not profile, so I cannot say how much time this saves.
2. The original code gave no reason for the sort beyond the rollup comment. Nothing in the repo records why it was there, so I did not add one.
