The deliveries CLI now prints "invalid date" to stderr and exits with status 2 for a bad date. All 8 tests pass, including two new CLI tests.

**The `parse_date` docstring was wrong.** It said the function returns None for anything that isn't a valid date. That only holds for text that doesn't look like a date, such as blank text or "tbc". A date-shaped value that doesn't exist, like `31/02/2026`, makes `read_date` call `date(...)`, which raises `ValueError`. `importer.read_orders` already relies on that, and its docstring describes it correctly.

A CLI that checked only for None would have crashed with a traceback on `31/02/2026`. So the CLI treats both a None result and a `ValueError` as an invalid date. You didn't ask for the `ValueError` case, but it is the same mistyped-date situation.

I corrected the docstrings of `parse_date` and `read_date` to say both behaviours. I left their behaviour alone, so the importer is unaffected.

**Tests:**
- Added `test_a_date_that_does_not_exist_raises` to `tests/test_dates.py`.
- Added `tests/test_cli.py`, covering "tbc" and `31/02/2026`. Both give status 2, "invalid date" on stderr and nothing on stdout.

No stated requirement of yours conflicted with the code. The conflict was only in the docstring, which I corrected.
