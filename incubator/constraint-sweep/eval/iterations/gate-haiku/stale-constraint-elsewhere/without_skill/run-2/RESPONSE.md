I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

Nothing in the codebase needs that sort:
- `alerts/spikes.py` `find_spikes` sorts its own input by time.
- `metrics/rollup.py` `hourly_rollup` sorts its own input by sensor and time, because `groupby` only groups adjacent items.
- `cli/export.py` already says line order does not matter.

I also corrected the comment in `metrics/rollup.py`. It said `hourly_rollup` relied on `load_readings` returning sorted data, which was never true because the function sorts for itself. The comment now says that.

The unit tests pass (4 of 4).

One caveat on the speed-up: `cli/report.py` still calls `hourly_rollup`, which sorts the readings again, so `report` only gets part of the gain. The rollup's sort is what makes it correct for any input order, so removing it would mean every caller has to pass pre-sorted data. I did not change that, since it is a contract change you should decide on.
