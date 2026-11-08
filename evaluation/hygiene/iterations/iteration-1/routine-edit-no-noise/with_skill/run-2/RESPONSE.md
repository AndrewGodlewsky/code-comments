I added a `--quiet` flag to the `report` command. When it is passed, the command no longer prints the "Wrote N rows to ..." line. Everything else is unchanged: the summary CSV is still written, the exit code is still 0, and without the flag the output is identical to before.

The change is in `cli/report.py`: a `store_true` option is registered in `build_parser()`, and the final `print` in `main()` is wrapped in `if not args.quiet:`. I did not add a comment, since the change is routine and the flag name explains itself.

I have not run the command or any tests, because none were requested and the repository has no test files that I looked at.
