I renamed the `export` command's `--since` option to `--after`. Its behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and leaving it out still writes every row. `--since` is removed with no alias, since only our own jobs call reportctl.

Changes:
- `app/cli.py`: the option is now `--after`, and the parsed value is read from `args.after`.
- `app/backfill.py`: the backfill now calls `export` with `--after`.
- `tests/test_cli.py`: the test now uses `--after` and is renamed to match.
- `docs/cli.md`, `README.md`, `docs/runbooks/backfill.md`: the examples and option table now use `--after`.
- `CHANGELOG.md`: a line under Unreleased records the rename.

The unit tests pass (3 of 3).

One thing I left alone: `docs/adr/0002-incremental-export.md` still says `--since`. It is an accepted decision record, so I did not rewrite it. If you want it current, either add a short note that the option was renamed to `--after` in the next release, or edit the text directly. The older CHANGELOG entry for 1.2.0 also still says `--since`, which is correct for that release.

If any of your jobs or scripts outside this repository still pass `--since`, they will now fail with an unrecognised-argument error. Update them to `--after` before deploying.
