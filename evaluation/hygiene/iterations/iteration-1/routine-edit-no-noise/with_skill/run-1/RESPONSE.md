I added a `--quiet` flag to the `report` command. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Everything else is unchanged: the CSV output, the `--region` filter, the exit code and the default output are the same as before.

The change is in `cli/report.py`: a `store_true` argument in `build_parser()`, and the final `print` in `main()` is now guarded by `if not args.quiet:`. I did not add a comment, since this is a routine change and the existing comments remain accurate.

I checked it by running `main()` with and without `--quiet` on a small sample file. Both runs returned 0 and wrote identical CSV output. With `--quiet` nothing was printed, and `--region` still filtered correctly. I did not add a test file, and I did not commit anything.
