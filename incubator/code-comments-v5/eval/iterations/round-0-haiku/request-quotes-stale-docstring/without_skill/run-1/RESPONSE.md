The deliveries CLI now reports an invalid date and exits with status 2.

In `deliveries/cli.py`, `main` checks the result of `parse_date`. When it gets None, it prints "invalid date" to stderr and returns 2. A valid date still prints the delivery date and returns 0.

One thing you should know: the docstring of `parse_date` is out of date for impossible dates. It says the function returns None when the text is not a valid date, but a date in the right shape that does not exist, such as `31/02/2026`, makes `parse_date` raise ValueError instead. `read_orders` in `deliveries/importer.py` depends on that ValueError to list the typo line. So I did not change `parse_date`. To keep the CLI clear for those inputs too, I catch the ValueError in `main` and treat it the same way as None. Without that, a mistyped date like `31/02/2026` would have crashed with a traceback.

Checked by running the CLI from the repository root:
- `2026-03-14` prints `2026-03-17` and exits 0.
- `tbc` prints `invalid date` to stderr and exits 2.
- `31/02/2026` prints `invalid date` to stderr and exits 2.

The existing five tests still pass. I did not add tests for the CLI, since you did not ask for them.

Suggested follow-up: correct the `parse_date` docstring to say that it returns None for text that is not in a known shape and raises ValueError for a date that does not exist, or change the function so both cases behave the same way. Either change touches the importer, so I left it for you to decide.
