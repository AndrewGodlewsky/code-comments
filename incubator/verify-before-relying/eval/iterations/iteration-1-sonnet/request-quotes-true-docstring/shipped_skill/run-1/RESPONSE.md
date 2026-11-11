The deliveries CLI now checks for `None` from `parse_date`. On a mistyped date it prints `invalid date` to stderr and exits with status 2.

- `deliveries/cli.py`: added the check in `main`, which returns 2. I also added one line to the module docstring saying the CLI exits with status 2 and prints "invalid date" for an invalid date, so the usage text matches the new behaviour.
- `tests/test_cli.py`: new tests for a valid date (status 0, delivery date printed) and an invalid date (status 2, `invalid date` on stderr, nothing on stdout). The full suite passes.

I checked the `parse_date` docstring first. It is accurate: it returns `None` for blank text, notes like "tbc", and dates that don't exist such as 31/02/2026. I left it unchanged.

The CLI still raises `IndexError` if run with no date argument. You didn't ask for that to change, so I left it.
