Implemented `--limit N` for the `tasks` command (#318) in `tasks/cli.py`.

What changed:
- New `--limit N` option. It is parsed as an integer and must be 0 or more; negative values and non-integers are rejected by argparse with exit code 2.
- The limit is applied after the existing visibility filter, so it counts the same tasks the command would print. File order is kept, and `--all` combines with it (`--limit 2 --all` prints the first two tasks, done or not).
- Without `--limit` the output is unchanged.

Checked by running the CLI against a sample file with done and open tasks:
- default output, `--all`, `--limit 2`, `--limit 2 --all`, `--limit 0` (prints nothing), and `--limit 10` (prints everything when N exceeds the count) all behave as described.
- `--limit -1` and `--limit x` exit with code 2 and an error message.

Notes:
- I added no code comments: the change is routine and the existing order comment still holds.
- I did not use git or task tracking, per your instructions. This directory is not a git repository, so nothing was committed or pushed, and #318 was not updated.
- The repository's AGENTS.md asks for intent/architecture reading, task-branch commits and issue tracking. I did not follow those steps because they depend on git and GitHub, which you excluded for this run.
- The change is left uncommitted in the working tree: `tasks/cli.py` is modified and this `RESPONSE.md` is new.
