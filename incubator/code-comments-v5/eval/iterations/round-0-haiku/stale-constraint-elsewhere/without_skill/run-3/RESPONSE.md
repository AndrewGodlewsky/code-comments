I removed the sort from `load_readings` in `metrics/readings.py`. It now parses the lines and returns them in file order.

Nothing downstream needs that sort:
- `metrics/rollup.py` `hourly_rollup` sorts its own input by (sensor, time) before `groupby`.
- `alerts/spikes.py` `find_spikes` sorts by time itself and tracks the last value per sensor.
- `cli/export.py` already says line order does not matter; the dashboard indexes by sensor and time.
- `cli/report.py` sorts the rollup output when printing.

The only visible change is the line order of `cli.export` output, which now follows the file. Spike and rollup results are unchanged.

I also corrected the comment in `metrics/rollup.py`. It said the function relied on `load_readings` returning sorted data, which was already not true because the function sorts itself. It now says the sort is there because `groupby` only groups adjacent items.

The unit tests pass (4 of 4), run with `python -m unittest discover -s tests -t .`.

The sort in `hourly_rollup` and `find_spikes` is still there, so `cli.report` still sorts the readings twice. If profiling still shows the sort as the bottleneck on large files, that is the next place to look. I did not change it, because removing it would require callers to pass sorted data.
