I added a `--quiet` option to the `report` command. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Everything else is unchanged.

The change is in `cli/report.py`:
- `build_parser()` has a new `--quiet` flag (`store_true`).
- `main()` only calls the `print` for the summary line when `args.quiet` is false.

I checked it by calling `main()` directly from a temporary source CSV. Without the flag it printed `Wrote 2 rows to t_out.csv`. With `--quiet` it printed nothing, and the output CSV was written the same in both cases. I did not add tests, because the repository has no test suite for this command.

No existing comments or docstrings became false, so I left them as they were.
