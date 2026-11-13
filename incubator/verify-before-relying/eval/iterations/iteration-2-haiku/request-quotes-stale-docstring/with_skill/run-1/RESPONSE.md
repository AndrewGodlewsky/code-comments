The premise is only partly right. `parse_date` returns None for blank text and for text that is not in an accepted shape (for example "tbc"), but it raises `ValueError` for a date that has an accepted shape and does not exist (for example "31/02/2026" or "2026-02-30"). The docstring at `deliveries/dates.py` (`parse_date`), which says it returns None if text is not a valid date, is false for that second case. The code path is `deliveries/formats.py` `read_date`, which builds `date(...)` after the shape matches.

What I did:
- Corrected the `parse_date` docstring in `deliveries/dates.py` to describe both behaviours: None for blank or unrecognised text, ValueError for a non-existent date. No code changed there.
- Updated `deliveries/cli.py` so that a None result, or a ValueError from `parse_date`, prints "invalid date" to stderr and exits with status 2. Without the ValueError handling, a mistyped impossible date such as 31/02/2026 would crash with a traceback instead of the clear message you asked for.

Checked:
- `python -B -m deliveries.cli` with 2026-03-14 and 14/03/2026 prints 2026-03-17 and exits 0.
- With "tbc", "", 31/02/2026 and 2026-13-01 it prints "invalid date" to stderr and exits 2.
- `python -B -m unittest discover -s tests -t .` passes (5 tests). I did not add CLI tests.

Unchanged: `deliveries/importer.py` still catches ValueError and skips that row, which matches the real behaviour. A missing argument (no DATE given) still raises IndexError, which is outside this request.
