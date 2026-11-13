The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date can't be read.

One thing to know first: `parse_date` does not return None for invalid input. Its docstring says it does, but the code in `deliveries/dates.py` only returns None for blank text. For anything that isn't a date in a known format (ISO or day/month/year), `parse_any` raises `ValueError`, and the existing test `test_text_that_is_not_a_date_raises` asserts exactly that. Checking only for None would therefore never fire for a mistyped date, and the user would still get a traceback.

So in `deliveries/cli.py` I handle both cases. The CLI catches `ValueError` from `parse_date` and also treats a None result as invalid. Either way it prints "invalid date" to stderr and returns 2:

- `2026-03-14` prints `2026-03-17` and exits 0.
- `next tuesday` prints "invalid date" to stderr and exits 2.
- A blank argument prints "invalid date" to stderr and exits 2.

The 5 existing unit tests pass. I did not add a CLI test.

I did not change the `parse_date` docstring, which is now wrong. It should say that invalid text raises ValueError and that None is returned only for blank input. Say if you want me to fix it.
