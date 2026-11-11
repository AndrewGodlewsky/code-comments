The deliveries CLI now checks for None from parse_date. In `deliveries/cli.py`, `main` prints "invalid date" to stderr and returns 2, and the `__main__` block passes that to `sys.exit`, so the exit status is 2.

I checked the docstring before relying on it. `parse_date` ("Return the date written in text, or None if text is not a valid date") is accurate. It strips the text and calls `read_date` in `deliveries/formats.py`, which returns None when no format fits or the date does not exist. The tests in `tests/test_dates.py` pin None for blank text and for "tbc". I also ran it on "2026-02-30", "31/02/2026" and "14/13/2026", and each returned None without raising. I left the docstring as it is and added no extra guards.

I ran the CLI with `2026-02-30`. It printed "invalid date" and exited with status 2. A valid date (`2026-03-14`) still prints the delivery date and exits 0. I did not add tests for the new CLI path.
