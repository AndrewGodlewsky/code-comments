I added a `--quiet` option to the report command. When it is passed, the `Wrote N rows to ...` line is not printed. Without it, output is unchanged.

The change is in `cli/report.py`:
- `build_parser()` has a new `--quiet` flag (`store_true`, help text "do not print the row count").
- `main()` only prints the `Wrote N rows` line when `--quiet` is not set. The CSV is still written and the exit code is still 0.

I checked it by calling `main()` directly in a temporary folder:
- Without `--quiet`, the line is printed as before.
- With `--quiet`, nothing is printed, and the output CSV is correct (including with `--region`).
- `--help` lists the new option.

I did not commit anything, and I left the existing `--region` comment as it was. The temporary test folder and `__pycache__` were removed.
