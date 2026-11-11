I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the function body is a single list comprehension.

What I checked before changing it, by grepping every file in the repo (all types) for `load_readings`, `sort`, `order`, `group` and `readings`:

- `metrics/rollup.py`: the comment said `hourly_rollup` relies on `load_readings` returning readings grouped by sensor and in time order. That was already not true in practice, because `hourly_rollup` sorts its own input before `groupby`. I rewrote the comment to say the function sorts its own input and that `load_readings` returns file order. Behaviour is unchanged.
- `alerts/spikes.py`: `find_spikes` sorts by `at` itself, so it does not depend on load order.
- `cli/report.py`: the rollup is sorted when printed, so output is unchanged. Spike lines are printed in `find_spikes` order.
- `cli/export.py`: its comment already says line order does not matter. The JSON-lines output now follows file order instead of sensor-then-time order.
- `tests/test_readings.py` sorts the values it checks, and `tests/test_rollup.py` feeds shuffled input, so neither depends on the removed sort.
- `README.md` and the module docstring say nothing about output order. I updated the `load_readings` docstring to say "in file order (not sorted)".

One behaviour change to know about: `cli/report.py` may print spike lines in a different order when two sensors have a spike at the same timestamp. Previously the input to `find_spikes` was sorted by sensor then time, so ties were ordered by sensor name. Now they follow file order. Within a single sensor, the order is unchanged.

Verification: `python -m unittest discover -s tests -t .` passes (4 tests). A quick check on a three-line file showed the loader returns file order and the rollup gives the same means as before.

Not verified: I did not profile on a big gateway file, since none is in the repo. The sort is O(n log n) on tuples, so it is a plausible cost, but parsing may still dominate. Please confirm the speedup on a real file.
