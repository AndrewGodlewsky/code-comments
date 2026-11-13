I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and its docstring says so.

Before changing it I grepped the whole repository (all file types, including README and comments) for `load_readings`, `sort` and `order`. Findings:

- `cli/export.py` already says line order does not matter (the dashboard indexes by sensor and time). Unaffected.
- `cli/report.py` passes the readings to `hourly_rollup` and `find_spikes`, and sorts its own output. Unaffected.
- `metrics/rollup.py` had a comment saying it relies on `load_readings` returning readings grouped by sensor and in time order. That is no longer true, and it was already not needed: `hourly_rollup` sorts its own input, because `groupby` only groups adjacent items. I rewrote the comment to say that. I left the sort in `rollup.py` because it is required for correctness there. It is a second O(n log n) sort on the same data, so if the profile is still dominated by sorting, that is the next place to look.
- `alerts/spikes.py` sorts by time itself, so it does not depend on load order.
- `tests/test_readings.py` compares sorted values, so it is order-insensitive. `tests/test_rollup.py` already covers shuffled input.
- `README.md` only says `load_readings` parses a file. It states no ordering, so I left it alone.

Tests: `python -m unittest discover -s tests -t .` passes (4 tests). I did not profile the change on a large gateway file, so the speed-up is not measured. I also did not add a test that pins the new file-order behaviour.
