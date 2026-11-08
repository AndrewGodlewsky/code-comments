I added a `--quiet` flag to the `report` command in `cli/report.py`. When it is passed, the command no longer prints the `Wrote N rows to <output>` line. Everything else is unchanged: the CSV is still written, the exit code is still 0, and without the flag the output is the same as before.

What changed:
- `build_parser()` gets `--quiet` as a store-true option with a short help string.
- `main()` prints the summary line only when `--quiet` is not set.

I checked it by calling `main()` directly with and without the flag, including with `--region`. The default run printed `Wrote 2 rows to ...`, and the quiet runs printed nothing and still wrote the correct output file. I removed the test files afterward.

I did not change any comments. The existing comment on `--region` still holds.
