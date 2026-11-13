The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date can't be read.

The change is in `deliveries/cli.py`. `main()` catches the `ValueError` that `parse_date` raises and treats it as `None`, then checks for `None` and prints the message. Valid dates still print the delivery date and exit 0.

One thing you should know: `parse_date` does not return `None` for invalid text. Its docstring says it does, but `parse_any` raises `ValueError` for any non-blank text in an unknown format, and the existing tests in `tests/test_dates.py` assert that. `parse_date` only returns `None` for blank input. Because of that, a `None`-only check would have missed a mistyped date like "next tuesday", which is the case you care about. The CLI now handles both paths.

Checked by hand:
- `2026-03-14` prints `2026-03-17` and exits 0.
- `14/03/2026` prints `2026-03-17` and exits 0.
- `next tuesday`, `2026-13-45` and blank input each print `invalid date` to stderr and exit 2.
- The existing unit tests pass (5 of 5).

I did not change `deliveries/dates.py`. Its docstring is wrong about invalid input and should say that `parse_date` raises `ValueError` for text that is not a date, returning `None` only for blank input. I left it alone because you asked only for the CLI change. I also did not add tests for the CLI.
