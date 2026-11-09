I added a `--quiet` flag to the report command in `cli/report.py`. When it is passed, the "Wrote N rows to ..." line is not printed. Everything else is unchanged: the summary CSV is still written, `--output` and `--region` behave as before, and the exit code is still 0.

The change is two edits:
- `build_parser()` gets `--quiet` as a `store_true` option.
- `main()` wraps the existing print in `if not args.quiet:`.

I checked it by calling `main()` directly on a small sample CSV. Without the flag the message prints as before. With `--quiet`, and with `--quiet --region north`, nothing is printed, the output file is written with the right totals, and the return value is 0.

I did not add a code comment, since this is a routine flag with no reason the next editor needs. I did not run git or commit anything.
