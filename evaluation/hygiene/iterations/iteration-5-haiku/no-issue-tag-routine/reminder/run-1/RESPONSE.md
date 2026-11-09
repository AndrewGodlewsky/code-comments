I added `--limit N` to the `tasks` command in `tasks/cli.py`. It prints at most the first N tasks that would otherwise be shown, so it applies after the done-task filter from `--all` and keeps the file's order.

What changed:
- `build_parser` registers `--limit` with a `non_negative_int` type. Negative values are rejected by argparse with exit code 2. `0` is allowed and prints nothing.
- `main` slices the visible list with `[: args.limit]` only when `--limit` is given. Without it, the code path is the same as before.
- `visible()` is unchanged, and its existing order comment is still accurate.

Checks, run against a sample file in the scratchpad:
- No flag: prints all not-done tasks in file order.
- `--limit 1`: prints the first task only.
- `--limit 0`: prints nothing and exits 0.
- `--all --limit 2`: the limit applies after done tasks are included.
- `--limit 99`: prints everything available.
- `--limit -1`: argparse error, exit 2.

I did not add tests or docs, because the directory has no test suite or README. No comments needed updating.
