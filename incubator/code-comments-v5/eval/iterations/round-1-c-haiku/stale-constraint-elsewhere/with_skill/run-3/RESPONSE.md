I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

I checked the callers before removing it:

- `metrics/rollup.py` `hourly_rollup` has a comment saying it relies on `load_readings` returning readings grouped by sensor and in time order. That was false: `hourly_rollup` already sorts its input itself. I corrected the comment to say the sort lives there because `groupby` only groups adjacent items and readings arrive in any order. The rollup means are unchanged.
- `alerts/spikes.py` `find_spikes` sorts by time itself, so the spike set is unchanged.
- `cli/export.py` already states that line order does not matter.
- `cli/report.py` prints the rollup in sorted order.

One observable change: when two sensors have spikes at the exact same timestamp, `cli/report.py` may print those SPIKE lines in file order rather than sensor order. The set of spikes does not change.

I did not benchmark the speedup, so the profiling claim is still unverified. The 4 existing unit tests pass. No test covers the new file-order contract, so I did not add one.
