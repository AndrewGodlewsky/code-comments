The premise in the request is partly wrong. `parse_date` does not always return None for an invalid date. Its docstring in `deliveries/dates.py` says "or None if text is not a valid date", but I probed the code:

- Text in no accepted shape, such as `tbc` or blank text, returns None.
- Text in an accepted shape that names a day that does not exist, such as `31/02/2026` or `2026-02-31`, raises ValueError. The `read_orders` importer and its test already depend on that behaviour, and the test expects the line to be skipped.

I corrected the docstring in `deliveries/dates.py` to describe both outcomes.

The CLI change in `deliveries/cli.py` handles both cases, so a mistyped date gets the clear error in either form:

- `parse_date` raising ValueError is caught and treated as no date.
- A None result prints `invalid date` to stderr and returns status 2.
- Valid dates behave as before.

Checks run from the shell with `python -B`:

- `14/03/2026` prints `2026-03-17` and exits 0.
- `tbc` prints `invalid date` to stderr and exits 2.
- `31/02/2026` prints `invalid date` to stderr and exits 2.
- The existing 5 unit tests pass.

I did not add a CLI test file, and I did not commit anything.
