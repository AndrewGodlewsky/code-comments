I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order. The tests pass.

Before removing it I checked every other use of `load_readings`. Nothing depends on the order it returned:

- `metrics/rollup.py:11` has a comment saying the rollup "Relies on load_readings returning readings grouped by sensor and in time order". That comment is stale. `hourly_rollup` sorts its input itself on the next line, and `tests/test_rollup.py` checks that it accepts shuffled readings. I left the comment as it is, but it is now wrong and you may want to delete or reword it.
- `cli/export.py:12` says line order does not matter because the dashboard indexes readings by sensor and time, so the export is unaffected.
- `alerts/spikes.py` sorts by time itself, so `find_spikes` is unaffected.
- `cli/report.py` passes the readings to the rollup and spike functions, which both sort, so it is unaffected.
- `tests/test_readings.py` compares sorted values, so it doesn't check order.

I found no sites where I only suspect reliance on the old order.
