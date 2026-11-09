I added `--limit N` to the `tasks` command in `tasks/cli.py`. It prints at most the first N tasks from the list it would otherwise show, so it applies after the done-task filter and `--all` is respected (`--all --limit 3` prints the first three tasks including done ones). Without `--limit`, output is unchanged.

Details:
- `--limit` takes a non-negative integer. `--limit 0` prints nothing, a value larger than the list prints everything, and negative or non-integer values are rejected by argparse with exit code 2.
- The limit is applied after `visible()`, so the file's order is preserved, which the existing comment in `visible()` still describes accurately. I did not need to change any comments or docstrings.

Verification: I ran the command against a five-task sample (two done) from a scratch script outside the repo. Default output, `--all`, `--limit 2`, `--limit 0`, `--limit 9`, `--all --limit 3`, and the invalid values all behaved as described. The repo has no test suite, so I did not add tests.
