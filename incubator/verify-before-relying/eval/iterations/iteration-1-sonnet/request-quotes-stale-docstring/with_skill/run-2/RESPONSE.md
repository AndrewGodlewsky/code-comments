One premise in your request is wrong. `parse_date` does not return None for every invalid date (`deliveries/dates.py:7`, docstring). It returns None only for text in no recognised format (`tbc`, blank, `abc`). For a well-formed date that does not exist, such as `31/02/2026` or `2026-02-30`, `read_date` (`deliveries/formats.py:19`) calls `date(...)`, which raises `ValueError`. I confirmed this by running it. `deliveries/importer.py:17-21` and `tests/test_importer.py` already rely on that `ValueError`.

A None-only check would have let a mistyped date like 31/02/2026 crash with a traceback, so the CLI now handles both. In `deliveries/cli.py`, `main` treats either a None result or a `ValueError` as invalid. It prints "invalid date" to stderr and returns 2, which `sys.exit` turns into exit status 2.

I corrected the two docstrings that described this wrongly, to match the code. `parse_date` now says None for an unrecognised format and `ValueError` for a nonexistent date. `read_date` now also mentions the `ValueError`. I left the behaviour of both alone.

I added `tests/test_cli.py`, covering a valid date, `tbc` and `31/02/2026`. The full test suite passes.
