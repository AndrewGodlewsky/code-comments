Added `--limit N` to the `tasks` command (#318).

Changes are in `tasks/cli.py`:

- `--limit N` caps the output at the first N tasks that would otherwise be shown. The cap is applied after the done-task filter, so `--all --limit 2` prints the first two tasks including done ones, and the default view prints the first two open tasks.
- `--limit 0` prints nothing. Negative values are rejected by argparse with an error (exit code 2), because slicing with a negative number would silently drop tasks from the end.
- Without `--limit` the code path is unchanged: the default is `None` and the slice is skipped.
- File order is preserved, as before.

I checked this with a small fixture (four tasks, one done) outside the repository: no flag, `--limit 1`, `--limit 0`, `--limit 9`, `--all --limit 2`, and `--limit -1`, all behaved as described. The repository has no test suite, so I did not add tests.

No comment was added to the code. The change is routine, and the existing "keep the file's order" comment is still accurate.

The changes are uncommitted, and I did not use git or GitHub, as you asked.
