The deliveries CLI now checks for None from `parse_date`. In `deliveries/cli.py`, `main` prints "invalid date" to stderr and returns 2, which `sys.exit(main())` turns into exit status 2.

I checked the claim in your request first. The `parse_date` docstring (`deliveries/dates.py:27`) says it returns None for something that isn't a valid date, and that is true. `parse_date` passes the text to `read_date` (`deliveries/formats.py:13-23`), which returns None when no format fits or when the date doesn't exist. `tests/test_dates.py` covers blank text and "tbc". I also ran it on "2026-13-45", "31/02/2026", "abc" and an empty string. All returned None and none raised. I left the docstring unchanged and added no extra guards.

Manual runs: `python -m deliveries.cli 2026-13-45` prints "invalid date" to stderr and exits with 2. A valid date still prints the delivery date and exits with 0. I did not add a CLI test.
