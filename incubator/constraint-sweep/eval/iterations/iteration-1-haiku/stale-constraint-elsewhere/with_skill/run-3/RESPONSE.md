I removed the sort from `load_readings` in `metrics/readings.py`. The function now returns the parsed readings in file order, and the `readings.sort(...)` line is gone.

Before the change I searched the repository for `load_readings`, `metrics.readings` and `metrics/readings`, and read every hit. Nothing downstream needs the readings sorted by sensor and time:

- `metrics/rollup.py` `hourly_rollup` sorts its own input by (sensor, time) before grouping, so its results are unchanged.
- `alerts/spikes.py` `find_spikes` sorts by time itself and compares each sensor only with its own previous reading. Its per-sensor sequence is the same as before, so the spikes are the same.
- `cli/report.py` sorts the rollup output before printing, so its output is unchanged.
- `cli/export.py` has a comment at line 12 saying line order does not matter. Its JSON lines now follow file order rather than sensor and time order. This is the one visible output change, and the existing comment already accepts it.
- The unit tests do not depend on order.

Stale constraint (not blocking, reported only):
- `metrics/rollup.py:11-12` says "Relies on load_readings returning readings grouped by sensor and in time order: groupby only groups adjacent items." The function already sorts its input at line 13, so it did not rely on this before the change. The comment is stale. After this change it also describes an ordering that `load_readings` no longer provides. I did not edit it, because the wording fix belongs under the code-comments skill.

No suspected reliance sites remain.

Verification: `python -m unittest discover -s tests -t .` runs 4 tests, all passing. I did not profile the speedup, and I did not commit anything.
