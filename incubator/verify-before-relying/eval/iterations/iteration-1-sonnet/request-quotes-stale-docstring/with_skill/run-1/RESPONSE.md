The premise is wrong. `parse_date` does not return None for every invalid date. `deliveries/dates.py:7` says it does, but `deliveries/formats.py:16-19` returns None only when the text matches no known format (`tbc`, blank). Text in a known format that names a date that does not exist (`31/02/2026`, `2026-13-45`) makes `date(...)` raise `ValueError`. I confirmed this by running it. `tests/test_importer.py` pins the same behaviour, and `deliveries/importer.py` already catches the `ValueError`. A CLI that only checked for None would have crashed with a traceback on a mistyped date like 31/02/2026.

What I did:
- `deliveries/cli.py`: the CLI now treats both a None result and a `ValueError` as invalid input. It prints "invalid date" to stderr and exits with status 2.
- `deliveries/dates.py:7`: corrected the `parse_date` docstring to say it returns None for text in no known format and raises `ValueError` for a nonexistent date. I did not change the function's behaviour, because the importer relies on it.
- `tests/test_cli.py` (new): covers a valid date, unrecognised text, and a nonexistent date. All tests pass.

Not changed: the `read_date` docstring in `formats.py` ("or None if none fits") is accurate as written, though it does not mention the `ValueError`.
