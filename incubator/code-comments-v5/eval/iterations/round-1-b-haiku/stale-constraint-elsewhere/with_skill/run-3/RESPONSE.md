I removed the sort from `load_readings` in `metrics/readings.py`. It now returns readings in file order, and the docstring says so.

I checked every caller before removing it:
- `metrics/rollup.py` (`hourly_rollup`) sorts its own input, so it did not depend on the sort. Its comment said it relied on `load_readings` returning readings grouped by sensor and in time order. That claim was no longer true, so I rewrote the comment to say the function sorts its own input and why (`groupby` only groups adjacent items).
- `alerts/spikes.py` (`find_spikes`) sorts by time itself, so it is unaffected.
- `cli/export.py` says line order does not matter, and the dashboard indexes by sensor and time, so it is unaffected.
- `cli/report.py` sorts its output, so it is unaffected.

The unit tests pass (4 tests, `python -m unittest discover -s tests -t .`).

Not verified: I did not run a profile, so I have not confirmed that the sort is the slow part of `load_readings` on the big gateway files. Also, `hourly_rollup` still sorts the same data on the `report` path, so that cost remains. Removing that sort would bring back the ordering dependency the rollup comment now describes, so I left it alone.
