I added a `--quiet` flag to `report`. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Nothing else changes: the summary CSV is still written, `--region` and `--output` behave as before, and the exit code is still 0.

The change is in `cli/report.py`: a `store_true` argument in `build_parser()` and a guard around the existing `print` in `main()`.

I checked it by parsing the arguments with and without `--quiet`, and by running `main()` on a small sample CSV. Without the flag it printed the line; with it, nothing was printed and the output file had the expected totals. The repository has no test suite, so I did not add tests. I left the code uncommitted, as you asked.
