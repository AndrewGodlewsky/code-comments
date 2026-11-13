The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date isn't valid. The change is in `deliveries/cli.py`.

`parse_date`'s docstring is wrong about when it returns `None`. It does that only for blank text. A non-blank string that isn't a date, such as `next tuesday` or `2026-13-45`, raises `ValueError` from `parse_any`, and `tests/test_dates.py` confirms this. A check for `None` alone would still have crashed with a traceback on a mistyped date. So the CLI treats both a `None` result and a `ValueError` as an invalid date.

I ran it by hand with a valid date, `next tuesday` and a blank argument. The valid date printed its delivery date. The other two printed "invalid date" and exited with 2. I didn't add a test for the CLI. I left the `parse_date` docstring alone, but it should be corrected to say it raises `ValueError` for non-date text. I can do that if you want.
