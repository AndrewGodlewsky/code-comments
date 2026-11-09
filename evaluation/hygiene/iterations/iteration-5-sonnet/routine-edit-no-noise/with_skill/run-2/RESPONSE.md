I added a `--quiet` flag to the report command in `cli/report.py`. With it, the command no longer prints the "Wrote N rows to ..." line. The summary CSV is still written, and without the flag the output is the same as before.

I did not run it or any tests. I added no comments, because the change is routine and the code explains itself.
