I took the sort out of `load_readings`; it now returns readings in file order.

I checked the consumers first. `hourly_rollup` in metrics/rollup.py sorts by sensor and time before grouping, and `find_spikes` in alerts/spikes.py sorts by time, so neither depends on the order `load_readings` returns. `cli/export.py` says line order does not matter there, and `cli/report.py` only passes the readings on.

One comment was stale. The comment in `hourly_rollup` said it relied on `load_readings` returning readings grouped and in time order, but the code under it sorts its own input, and `test_rollup_accepts_readings_in_any_order` checks that. I rewrote the comment to say why the function sorts, and added "in file order" to the `load_readings` docstring. The tests pass.
