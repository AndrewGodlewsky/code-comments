I added a `--quiet` option to the report command in `cli/report.py`. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Without it, the output is unchanged.

The change is two edits in that file: a `--quiet` flag (`store_true`) registered in `build_parser()`, and the existing `print` in `main()` wrapped in `if not args.quiet:`. Nothing else in the command's behaviour changes; the CSV output, `--region` filtering and return code are the same.

I checked it by calling `main()` directly on a small sample file: without the flag it prints the "Wrote 2 rows" line, and with `--quiet --region north` it prints nothing while still writing the correct output file. I did not run the existing test suite, because this repository directory contains only the `cli` package.

No code comment was added, since this is a routine change that needs no new explanation. Nothing was committed.
