The deliveries CLI (`deliveries/cli.py`, `main`) now prints "invalid date" to stderr and exits with status 2 when `parse_date` returns None.

I checked the `parse_date` docstring ("or None if text is not a valid date") against the code. It holds. `parse_date` calls `read_date`, which returns None for text that matches no known shape and for dates that don't exist. The tests in `tests/test_dates.py` cover blank text and "tbc". I also ran it on "2026-13-45", "31/02/2026", "abc" and "2026-3-4". Each returned None and none raised. So I used the None check as you described, with no extra exception handling, and left the docstring as it was.

Running the CLI with "2026-13-45" prints "invalid date" and exits with 2. A valid date still prints the delivery date and exits with 0.

I did not change the case where no date argument is given at all. That still raises an IndexError, because it wasn't part of the request.
