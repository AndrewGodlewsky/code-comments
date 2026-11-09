I added `--limit N` to the `tasks` command (#318). It prints at most the first N tasks it would otherwise show, so `--all` and the done-task filter still apply before the limit, and file order is kept.

Changes, all in `tasks/cli.py`:
- New `--limit N` option. It must be a whole number of zero or more; a negative value or a non-number is rejected by argparse with exit code 2. I rejected negatives because a negative slice would silently drop tasks from the end instead of limiting output.
- `main` takes the visible list and slices it to N only when `--limit` is given.

Without `--limit`, output is unchanged.

Checked with a mocked file (no files written to the repository):
- no flags: prints the not-done tasks, as before
- `--all`: prints every task, as before
- `--limit 2`: first two not-done tasks
- `--limit 0`: prints nothing
- `--limit 10`: prints all not-done tasks when there are fewer than 10
- `--all --limit 2`: first two tasks including done ones
- `--limit -1` and `--limit x`: usage error, exit code 2

I did not add a code comment: this is a routine change, and the issue number belongs in the commit, not the code. I did not run git, so nothing is committed.
