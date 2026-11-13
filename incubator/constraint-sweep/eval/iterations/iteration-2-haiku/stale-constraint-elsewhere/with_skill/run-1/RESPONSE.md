I removed the sort from `load_readings` in `metrics/readings.py`. It now returns the parsed readings in file order, and the function is a plain list comprehension over the lines. The four unit tests pass (`python -m unittest discover -s tests -t .`).

Sweep results for `load_readings`:

- `metrics/rollup.py:11-12` (fixed in this change): the comment said `hourly_rollup` relies on `load_readings` returning readings grouped by sensor and in time order. That reliance was already gone, because `hourly_rollup` sorts its own input on the line below. After this change the comment would also be false about `load_readings`, so I deleted it. The rollup's own sort is untouched. It is now the only ordering `hourly_rollup` depends on, and it is the same key the removed sort used, so its cost is unchanged by this edit.
- `cli/export.py:12`: says line order does not matter because the dashboard indexes by sensor and time. Consistent with the change; left as it was.
- `alerts/spikes.py` and `cli/report.py`: `find_spikes` sorts its own input by time, and `report` only passes readings through, so neither depends on the removed sort. No edit.
- `metrics/readings.py` module docstring and `load_readings` docstring: state no ordering promise, so they stay accurate. No edit.
- `tests/test_readings.py` and `tests/test_rollup.py`: the load test sorts its own results, and the rollup test already feeds shuffled input. No edit.
- README: does not describe ordering. No edit.

No live constraint was broken. Nothing in the repository still needs `load_readings` output in sorted order.

Not done: I did not change the rollup's own `sorted(...)` call on line 13 of `metrics/rollup.py`. It is outside the function you named, and it is the ordering `groupby` actually needs. If the profile still shows the sort dominating after this change, that line is the next candidate, but it is a separate decision.

Git was not used in this run, per the instructions.
