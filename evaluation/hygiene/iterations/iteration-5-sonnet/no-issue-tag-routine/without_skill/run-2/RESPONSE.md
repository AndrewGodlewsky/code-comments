I added a `--limit N` option to the tasks command (#318) in `tasks/cli.py`.

- `--limit N` prints at most the first N tasks. The limit is applied after the done-task filtering, so with `--all` it counts done tasks too. The file's order is kept, as before.
- Without `--limit`, the output is exactly as before.
- `--limit 0` prints nothing. A negative N is rejected with an argparse error.

I checked it by hand against a small sample file (default, `--limit 2`, `--all --limit 3`, `--limit 0`). The repository has no test suite, so I did not add tests.
