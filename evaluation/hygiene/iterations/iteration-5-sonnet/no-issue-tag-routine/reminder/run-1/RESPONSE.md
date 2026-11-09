I added `--limit N` to the tasks command in `tasks/cli.py`. It prints at most the first N tasks it would otherwise show.

- The limit applies after the done-task filtering, so `--all --limit 2` gives the first two tasks of the full list. File order is kept.
- Without `--limit` the output is unchanged.
- `--limit 0` prints nothing. A negative value is rejected with an argparse error.
- I ran it by hand on a small file (default, `--limit 2`, `--all --limit 2`, `--limit 0`) and the output was as expected. There is no test suite in the directory, so I added no tests.
- No existing comments or docs became false, so I changed none and added none.
