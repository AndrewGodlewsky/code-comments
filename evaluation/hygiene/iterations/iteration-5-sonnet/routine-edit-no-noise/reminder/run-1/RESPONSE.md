Added a `--quiet` flag to the report command in `cli/report.py`. With it, the "Wrote N rows to ..." line is not printed. The summary file is still written and the exit code is unchanged. Without the flag, behaviour is as before.

I did not run it, and the repository has no tests. No comments or docs needed changes, and I added none.
