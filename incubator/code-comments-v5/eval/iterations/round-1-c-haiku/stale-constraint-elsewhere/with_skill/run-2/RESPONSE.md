I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order.

Every consumer in this repo handles its own ordering, so nothing else depended on the sort:
- `metrics/rollup.py` `hourly_rollup` sorts by sensor and time itself before `groupby`. I corrected its comment, which claimed it relied on `load_readings` order. That claim was no longer true.
- `alerts/spikes.py` `find_spikes` sorts by time itself.
- `cli/export.py` already states that line order does not matter.
- `tests/test_readings.py` compares values in sorted order.

The `load_readings` docstring now says it returns readings in file order rather than time order.

Checks: the 4 unit tests pass. I also ran a small unsorted three-line file through `load_readings`, `hourly_rollup` and `find_spikes`. The rollup and spike results were correct.

Two things to know:
- The speedup is only on the `load_readings` path. `cli/report.py` still sorts twice, once in `hourly_rollup` and once in `find_spikes`. If the profile shows that cost, the next step is to sort once in `report.py` and pass the sorted list down, or to make the two helpers accept pre-sorted input. I did not make that change because it goes beyond removing the sort you asked about.
- I did not measure the speedup on your large gateway files.
