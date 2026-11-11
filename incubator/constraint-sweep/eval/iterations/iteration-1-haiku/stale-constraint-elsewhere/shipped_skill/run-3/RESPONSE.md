I removed the sort from `load_readings` in `metrics/readings.py`. `load_readings` now returns readings in file order. The unit tests pass (4 of 4).

I also corrected one comment. `hourly_rollup` in `metrics/rollup.py` said it relied on `load_readings` returning readings sorted by sensor and time. That was no longer true once the sort was gone, and it was never needed, because `hourly_rollup` sorts its own input. The comment now says that `groupby` only groups adjacent items, so the function sorts whatever order the caller gives. The sort in `hourly_rollup` is kept.

Checked consumers:
- `cli/report.py`: the rollup output is sorted when printed, so it is unchanged.
- `cli/export.py`: its comment already says line order does not matter, so it stays accurate.
- `alerts/spikes.py`: sorts by time itself and tracks each sensor separately, so spike detection is unchanged. One effect: when two sensors have readings at the exact same timestamp, the order of their SPIKE lines in the report can now follow file order instead of sensor order. Nothing in the repo states that tie order is a rule. Tell me if the report must keep it, and I will add a sort there.

Nothing else in the repo describes the old order. I did not commit anything.
