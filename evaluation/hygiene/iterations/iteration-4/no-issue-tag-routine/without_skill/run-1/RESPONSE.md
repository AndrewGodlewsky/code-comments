I added a `--limit N` option to the `tasks` command (#318). It prints at most the first N tasks that would otherwise be shown, in file order, after the existing done-task filter is applied.

Changes are in `tasks/cli.py`:
- New `--limit` argument with a `non_negative_int` validator. Negative or non-integer values are rejected by argparse with exit code 2.
- `main` slices the already-filtered list when `--limit` is given. `visible()` is unchanged.

Without `--limit` the default is `None`, so output is identical to before.

Checked with a small sample file (two open tasks, one done, one more open):
- no flags: three open tasks
- `--all`: all four tasks
- `--limit 2`: first two open tasks
- `--limit 0`: no output
- `--limit 10 --all`: all four tasks
- `--limit -1` and `--limit x`: usage error, exit 2

I did not add a test file, since the repo has no existing tests to follow.
