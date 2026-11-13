I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order.

Nothing else relied on that sort:
- `metrics/rollup.py` `hourly_rollup` sorts by sensor and time itself before its `groupby`. Its comment claimed it relied on `load_readings` for order, which was no longer true, so I rewrote the comment to say the function sorts locally and input order does not matter.
- `alerts/spikes.py` `find_spikes` sorts by time itself.
- `cli/export.py` already states that line order does not matter.
- `tests/test_readings.py` sorts the results it compares.

I updated the `load_readings` docstring to state that the result is in file order and not sorted. The old sort was the only visible sign of that ordering guarantee, so without this note the next editor could assume an order that no longer exists.

The unit tests pass (4 tests).

Two things to check:
- `cli/report.py` still sorts twice, once in `hourly_rollup` and once in `find_spikes`. If the slow part you profiled was the sort inside `load_readings`, that is now gone, but the report path still pays for two sorts on the large files. Sharing one sorted list between the two functions would remove that cost. I did not change this because you asked only for the sort in `load_readings` to go.
- I did not commit. The repository's git state is outside this exercise, so the change is only in the working files.
