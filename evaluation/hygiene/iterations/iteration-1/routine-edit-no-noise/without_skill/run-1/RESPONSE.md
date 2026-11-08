I added a `--quiet` flag to the report command. When it is passed, the `Wrote N rows to <output>` line is not printed. Everything else is unchanged.

The change is in `cli/report.py`:
- `build_parser()` has a new `--quiet` option (`store_true`, help text "do not print the 'Wrote N rows' line").
- `main()` only prints the summary line when `args.quiet` is false. The file write and the return value (0) are the same as before.

I checked it with a small sample CSV in a scratch directory outside the repo. Without the flag the output is `Wrote 2 rows to a.csv`. With `--quiet` nothing is printed, and the written CSV is identical to the one from the run without the flag. The return code is 0 in both cases.

I did not add tests because the repo has none for this module. I also did not use git.
