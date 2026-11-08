I added a `--quiet` flag to the report command in `cli/report.py`. When it is passed, the "Wrote N rows to ..." line is not printed. Without it, output is unchanged.

The change is two edits:
- `build_parser()` registers `--quiet` as a store-true flag.
- `main()` wraps the final `print` in `if not args.quiet:`.

Nothing else in the command changes. The CSV is still read and written the same way, the return value is still 0, and `--output`, `--region` and the rest behave as before.

I only checked that the file parses. I did not run the command end to end, so it is worth one run with and without `--quiet` before you rely on it.

I made no comment changes, since the change did not make any existing comment false. I did not commit anything.
