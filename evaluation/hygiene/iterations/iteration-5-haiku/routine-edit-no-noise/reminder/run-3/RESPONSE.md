I added a `--quiet` option to the `report` command. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Everything else is unchanged.

The change is in `cli/report.py`:
- `build_parser()` adds `--quiet` as a `store_true` flag, with help text "suppress the 'Wrote N rows' line".
- `main()` wraps the existing `print` in `if not args.quiet:`. The return value and the output CSV are the same as before.

No existing comment or docstring became false, so I did not touch any. I did not commit anything.

I checked it with a small script against a sample CSV. Without the flag, the call returns 0 and prints "Wrote 2 rows to ...". With `--quiet`, it returns 0, prints nothing, and writes the same summary CSV. This also held with `--region` combined with `--quiet`. I did not run a test suite, because the directory contains only `cli/report.py` and `cli/__init__.py`.
