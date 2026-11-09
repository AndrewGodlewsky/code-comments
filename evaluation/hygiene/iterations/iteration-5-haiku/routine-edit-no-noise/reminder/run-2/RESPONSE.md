I added a `--quiet` flag to the `report` command. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Everything else is unchanged.

The change is in `cli/report.py`:
- `build_parser()` registers `--quiet` as a `store_true` option with a short help string.
- `main()` wraps the existing print in `if not args.quiet:`. The CSV is still written and the return code is still 0.

I checked it by calling `main()` directly against a small sample CSV:
- Without `--quiet`, the output is `Wrote 2 rows to _o.csv`.
- With `--quiet`, nothing is printed and the return code is 0.
- With `--quiet --region north`, nothing is printed and the output CSV contains only the north rows.

I removed the temporary test files and `__pycache__` afterwards. No existing comments or docs became inaccurate, so I left them alone. I did not use git or GitHub.
