I added `--limit N` to the `tasks` command in `tasks/cli.py`. It prints at most the first N tasks it would otherwise show. The limit is applied after the done-task filter, so `--all --limit 2` gives the first two tasks of the full list. The file's order is kept. Without `--limit` the output is the same as before.

I ran it on a small sample file. `--limit 1`, `--all --limit 2` and no limit all printed what I expected.

Two things I did not do:
- I added no comments. The change is routine, and the existing comment about keeping the file's order still holds.
- I did not validate N. A negative value slices from the end of the list rather than being rejected. If you want an error for values below 0, say so.
