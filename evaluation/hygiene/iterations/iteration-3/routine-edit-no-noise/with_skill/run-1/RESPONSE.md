I added a `--quiet` option to the report command in `cli/report.py`. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Without it, output is unchanged.

The change is two edits in that file:
- `build_parser()` gets a `--quiet` flag (`action="store_true"`).
- `main()` prints the summary line only when `--quiet` is not set.

Everything else is untouched: the CSV is still written, the return value is still 0, and the region handling is the same.

I checked it with a small run against a sample CSV. The default call printed `Wrote 2 rows to scratch_a.csv`, and the `--quiet` call printed nothing. I did not run a formal test suite, since none exists in this directory. The changes are uncommitted.
