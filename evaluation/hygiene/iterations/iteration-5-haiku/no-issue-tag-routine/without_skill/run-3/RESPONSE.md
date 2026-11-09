I added `--limit N` to the `tasks` command (#318). It prints at most the first N tasks that would otherwise be shown.

What changed, all in `tasks/cli.py`:

- A new `--limit N` option. `N` must be a whole number of 0 or more. Negative or non-numeric values are rejected by argparse with exit code 2.
- The limit is applied after the existing `visible()` filter, so it counts tasks that are shown. Done tasks are skipped unless `--all` is passed, and file order is preserved, as before.
- Without `--limit`, the code path is the same as before: all visible tasks are printed.

Checks I ran against a temporary JSON file (four tasks, one done):

- no flag: prints a, c, d (unchanged)
- `--limit 2`: prints a, c
- `--limit 0`: prints nothing
- `--limit 9`: prints a, c, d
- `--all --limit 3`: prints a, b, c
- `--limit -1` and `--limit x`: rejected with an error

I did not add tests, since the repository contains only `tasks/cli.py` and an empty `tasks/__init__.py`. I also did not use git or any task tracker, as requested.
