I removed the sort from `load_readings` in `metrics/readings.py`. It now returns the parsed readings in file order. The unit tests pass (4 of 4).

Before the change I checked what depends on the order. Two mentions matter:

- `metrics/rollup.py:11-12` says hourly_rollup "relies on load_readings returning readings grouped by sensor and in time order". This is a stale constraint. `hourly_rollup` sorts its input itself (`metrics/rollup.py:13`), so it no longer depends on `load_readings` order. I left the comment unchanged because it is wording for `code-comments`. It is now inaccurate about `load_readings`, so it should be reworded or removed in a follow-up.
- `cli/export.py:12` says line order does not matter. This is consistent with the change.

`alerts/spikes.py` sorts its own input, and `cli/report.py` only passes readings through to `hourly_rollup` and `find_spikes`, which both sort. No live constraint binds the change.

Caveat: the `cli.report` path still sorts twice, once in `hourly_rollup` and once in `find_spikes`. Removing the sort in `load_readings` speeds up `cli.export` and any other caller that does not sort. It does not remove the sort cost from `cli.report`. I did not measure the speedup.
