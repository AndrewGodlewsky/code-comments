I added a `--limit N` option to the `tasks` command in `tasks/cli.py`.

- It prints at most the first N tasks that would otherwise be shown. The limit is applied after the `--all` filter, in file order, so the list is never re-sorted.
- Without `--limit`, behavior is unchanged.
- `--limit 0` prints nothing. A negative or non-integer value is rejected with an argparse error.

I checked it by hand on a small sample file (with and without `--all`, and with limits of 2 and 0). I did not add an automated test file.
