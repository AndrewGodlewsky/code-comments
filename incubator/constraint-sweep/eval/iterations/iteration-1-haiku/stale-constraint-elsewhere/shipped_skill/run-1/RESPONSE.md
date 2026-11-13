I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order.

Nothing downstream relied on that order:
- `hourly_rollup` (`metrics/rollup.py`) sorts by sensor and time itself, so I rewrote its comment. It used to say the rollup relied on `load_readings` order, which is no longer true. It now says the sort is there because `groupby` only groups adjacent items.
- `find_spikes` (`alerts/spikes.py`) sorts by time itself.
- `cli/export.py` already states that line order does not matter.

The unit tests pass (4 of 4).

Two things to check before you count the speedup:
- The `load_readings` sort is not the only one on the `cli.report` path. `hourly_rollup` and `find_spikes` each still sort the full list, so the report still does roughly two sorts. I did not benchmark the change, so the actual gain on your big gateway files is unmeasured.
- If you want the sort gone from the report path entirely, `hourly_rollup` and `find_spikes` would need to share one ordered input or drop their own sorts. That needs a decision from you, because both functions then depend on the caller's order again.
