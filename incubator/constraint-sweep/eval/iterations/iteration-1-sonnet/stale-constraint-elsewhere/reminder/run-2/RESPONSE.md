I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order. I haven't run the tests or timed it on a big gateway file.

I grepped the whole repo for `load_readings` before changing it. The two callers and the tests are unaffected:
- **`metrics/rollup.py`:** a comment said it "relies on load_readings returning readings grouped by sensor and in time order". That comment was stale. `hourly_rollup` already sorts its input itself before `groupby`, and `tests/test_rollup.py` checks that shuffled input works. I rewrote the comment to say the sort happens there and that `load_readings` gives no ordering.
- **`alerts/spikes.py`:** `find_spikes` sorts by time itself, so it doesn't depend on the loader's order.
- **`cli/export.py`:** a comment says line order doesn't matter because the dashboard indexes by sensor and time.
- **`cli/report.py`:** it only passes the result to the two functions above.
- **`tests/test_readings.py`:** it sorts the values before comparing, so it doesn't check order.

I also changed the `load_readings` docstring to say the result is in file order and callers must sort if they need an order. The module docstring already said gateway lines arrive out of time order.

**Behaviour change:** anyone outside this repo who relied on `load_readings` returning sorted data would now get file order. Nothing in the repo does.

**Slow path:** `hourly_rollup` and `find_spikes` each still sort the full list, so `cli/report` does two sorts of its own. If those are slow on big files, that is the next place to look.
