I added a `--quiet` option to the `report` command in `cli/report.py`. When it is passed, the command no longer prints the "Wrote N rows to ..." line. It is a boolean flag that defaults to off, so the output is unchanged without it.

The change is in two places:
- `build_parser()` registers `--quiet` as `store_true`, with a help string.
- `main()` wraps the existing `print` in `if not args.quiet:`.

Nothing else changed. The file is still written, the exit code is still 0, and `--region` and `--output` behave as before.

I checked this by calling `main()` directly with the null device as source and output, so no files were created:
- Without `--quiet`, it prints `Wrote 0 rows to NUL` and returns 0.
- With `--quiet`, it prints nothing and returns 0.
- `--quiet` combined with `--region eu` also prints nothing.
- The flag defaults to `False` when omitted.

I did not run the tool against a real sales CSV.
