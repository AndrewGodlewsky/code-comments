I added a `--limit N` option to the `tasks` command (#318). It prints at most the first N tasks that it would otherwise show, so `--all` and the done-task filter still apply before the limit. Without `--limit`, output is unchanged.

The change is in `tasks/cli.py`:
- A new `non_negative_int` argument type rejects negative values with a usage error. Zero is allowed and prints nothing.
- `--limit` is added to the parser with `metavar="N"`.
- `main` slices the result of `visible(...)` with `[: args.limit]`. When `--limit` is omitted, the slice is `None` and the full list is printed.

I checked this with a small sample file (two open tasks, one done, one more open) and a direct call to `main`:
- no flags: `a, c, d`
- `--all`: `a, b, c, d`
- `--limit 2`: `a, c`
- `--limit 0`: nothing
- `--limit 9`: `a, c, d`
- `--all --limit 3`: `a, b, c`
- `--limit -1`: usage error, exit code 2

I did not add a test file, since the repository has no test setup. The existing comment on `visible` ("Keep the file's order...") is still accurate, and no docs needed changing. I did not use git or GitHub, and nothing is committed.
