I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and I updated its docstring to say so. The tests pass.

Before editing I searched the repo for what other files say about `load_readings`.

**Stale comment, corrected:** `metrics/rollup.py:11-12` said `hourly_rollup` "relies on load_readings returning readings grouped by sensor and in time order". That is no longer true, and it was already stale, because `hourly_rollup` sorts its own input on the next line (and `test_rollup_accepts_readings_in_any_order` covers that). I reworded the comment to say the sort there is what makes `groupby` work. I left the sort in `hourly_rollup` alone.

**No other dependents:**
- `alerts/spikes.py` sorts by time itself.
- `cli/export.py:12` says line order doesn't matter.
- `cli/report.py` only passes the readings on to those two functions.
- `tests/test_readings.py` compares sorted values, so it doesn't depend on order either.

**Remaining cost:** `hourly_rollup` and `find_spikes` each still sort their input, so `cli/report.py` sorts twice per run. That is cheaper than before but still O(n log n). I didn't touch them because you only asked about `load_readings`. If `cli/report.py` is still slow on big files, those are the next place to look.
