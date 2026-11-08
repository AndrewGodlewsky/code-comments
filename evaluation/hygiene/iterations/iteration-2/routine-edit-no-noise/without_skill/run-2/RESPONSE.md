I added a `--quiet` flag to the `report` command. When it is passed, the command no longer prints the `Wrote N rows to <output>` line. Everything else is unchanged.

The change is in `cli/report.py`:
- `build_parser()` registers `--quiet` as a `store_true` flag with a help string.
- `main()` wraps the existing `print` in `if not args.quiet:`. The CSV is still written and the return value is still `0`.

I checked it by calling `main()` directly with and without `--quiet`, including combined with `--region`. Without the flag the message is printed as before. With it, nothing is printed and the output CSV is correct. I did not run it as a subprocess, and I did not add a test file, since the repo has no test suite.
