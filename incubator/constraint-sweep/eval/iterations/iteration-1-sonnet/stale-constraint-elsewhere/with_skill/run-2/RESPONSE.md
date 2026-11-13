I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, so the cost is one pass over the file. The tests pass.

Before removing it I checked every other mention of `load_readings`, because a sort like this can be what other code relies on.

- **Stale constraint, `metrics/rollup.py:11`:** the comment says `hourly_rollup` "Relies on load_readings returning readings grouped by sensor and in time order". That is no longer true. `hourly_rollup` sorts its input itself on the next line (`ordered = sorted(...)`), so it doesn't depend on `load_readings` for order. I left the file alone. The comment should be reworded or deleted.
- **`cli/export.py:12`:** it says line order doesn't matter, so the export is unaffected.
- **`alerts/spikes.py`:** `find_spikes` sorts by time itself, so it is unaffected. It is called from `cli/report.py` with the loaded readings.
- **Tests and README:** nothing there depends on the order. `tests/test_readings.py` already sorts the values before comparing.

One side effect is that `cli/report.py` and `cli/export.py` now emit readings in file order rather than sorted order. The rollup output in `report.py` is still sorted by its own call, and the spike output follows `find_spikes`' own sort. Nothing in the repo relies on the old order.
