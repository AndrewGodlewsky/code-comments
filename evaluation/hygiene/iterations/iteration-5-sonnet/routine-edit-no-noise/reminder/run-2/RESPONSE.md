I added a `--quiet` flag to the report command in `cli/report.py`. With it, the "Wrote N rows to ..." line is no longer printed. The summary file is still written and the exit code is still 0. Without the flag, behaviour is unchanged.

I didn't run it or any tests. No comments or docs referred to the output line, so none needed changing.
