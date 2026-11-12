I removed the sort from `load_readings` in `metrics/readings.py`. The function now returns the readings in file order.

Nothing else depended on that sort:
- `metrics/rollup.py` `hourly_rollup` already sorts its input by sensor and time itself before grouping, so its results are unchanged.
- `alerts/spikes.py` `find_spikes` sorts by time itself.
- `cli/export.py` already states that line order does not matter.

One comment was wrong after the change. The comment in `hourly_rollup` said it relied on `load_readings` returning readings grouped and in time order. It does not rely on that, because it sorts itself. I replaced it with "groupby only groups adjacent items, so sort by sensor and time first", which states the real reason for its own sort.

The unit tests pass (4 of 4) with `python -m unittest discover -s tests -t .`.

Note on the speed-up: `report` still sorts twice more (in `hourly_rollup` and `find_spikes`), so the saving is one of three sorts on that path. I did not touch those because you asked only for the sort in `load_readings`. If profiling still shows the sort as the bottleneck, `hourly_rollup` and `find_spikes` are the next candidates.
