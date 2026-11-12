I changed `main` in `deliveries/cli.py`. When `parse_date` returns None, the CLI now prints "invalid date" to stderr and exits with status 2. Valid dates behave as before.

I checked it two ways:
- `python -m unittest` in `tests/` passes (5 tests).
- `python -m deliveries.cli tbc` prints "invalid date" and exits 2. `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.

No comments were added, since the change is routine and I had no reason from the request or the code to record. No other file changed. I did not commit anything, because the task said not to use git.
