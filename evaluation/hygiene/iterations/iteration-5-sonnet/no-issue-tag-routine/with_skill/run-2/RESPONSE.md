I added `--limit N` to the `tasks` command in `tasks/cli.py`. It prints at most the first N tasks, counted after the done-task filter, in the file's order. For example, `--limit 1` on its own prints the first open task, and `--all --limit 2` prints the first two tasks of any status. Without `--limit` the output is the same as before.

A negative N is rejected with a parser error, because a negative slice would silently drop tasks from the end instead. You didn't specify this, so say if you'd rather handle it differently. `--limit 0` prints nothing.

I checked it by running the command on a small sample file with and without the flag. I didn't add any comments, since the change is routine and the existing comment on file order still holds.
