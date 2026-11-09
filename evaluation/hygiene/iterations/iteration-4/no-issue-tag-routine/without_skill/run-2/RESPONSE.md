I added a `--limit N` option to the `tasks` command (#318). It prints at most the first N tasks that would otherwise be shown. Without `--limit`, output is unchanged.

What changed, all in `tasks/cli.py`:

- `--limit` takes an integer `N`. The limit applies after the existing done-task filter, so `--limit 2` shows the first two visible tasks, and `--all` still includes done tasks in the count.
- Values below 0 and non-integers are rejected by argparse with exit code 2. `--limit 0` prints nothing.
- File order is preserved; the limit only truncates the list.

Verified by running `main()` against a four-task sample with one done task:
- No flag: prints the three not-done tasks, same as before.
- `--limit 2`: first two not-done tasks.
- `--limit 2 --all`: first two tasks including done ones.
- `--limit 0`: no output.
- `--limit 99`: all three.
- `--limit -1` and `--limit x`: usage error, exit 2.

No automated tests exist in this directory, so I did not add any. I also did not run git or touch anything outside this directory; the temporary sample file I used was deleted.
