I added `--limit N` to the `tasks` command in `tasks/cli.py`. It prints at most the first N tasks that it would otherwise show, after the existing `--all` filter and in file order. Without `--limit`, the output is unchanged.

Behaviour I checked against a sample file (run through `main()` directly, since the package has no installed entry point):
- no flag: unchanged (only open tasks)
- `--all`: unchanged (all tasks)
- `--limit 2`: first two open tasks
- `--limit 0`: prints nothing, exit 0
- `--limit 10`: more than exist, prints all of them
- `--all --limit 3`: first three tasks including done ones
- `--limit -1` and `--limit x`: argparse error, exit 2

Decision for you: negative values are rejected with an error rather than treated as "no limit" or as slicing from the end. Say if you want a different rule.

No comments were added or changed. The one existing comment on `visible()` (keep the file's order, never sort) is still true, and the new code is simple enough not to need one. The package has no test suite, so the checks above were manual.
