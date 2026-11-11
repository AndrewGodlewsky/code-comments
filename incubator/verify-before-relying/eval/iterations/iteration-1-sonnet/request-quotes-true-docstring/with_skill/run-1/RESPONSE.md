The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when `parse_date` returns None. The change is in `deliveries/cli.py`, in `main`.

I checked the docstring claim before relying on it, and it holds. `parse_date` (`deliveries/dates.py:6`) hands off to `read_date` (`deliveries/formats.py:13`). `read_date` returns None for text that fits no format and for dates that don't exist, and it does not raise. I ran `2026-13-45`, `31/02/2026`, an empty string and `abc`, and each returned None. The tests in `tests/test_dates.py` also pin None for blank text and for "tbc". I left the docstring as it was.

I ran the CLI by hand. `2026-13-45` prints "invalid date" to stderr with exit status 2, and `2026-03-14` still prints the delivery date with exit status 0. I did not add tests for the new CLI behaviour.

Running the CLI with no date argument still fails with an `IndexError`. You didn't ask about that, so I left it alone.
