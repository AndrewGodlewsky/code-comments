The premise is partly wrong. `parse_date` does not return None for every invalid date. It returns None only when the text has no recognised date shape, such as `tbc` or blank input. When the text has a date shape but names a day that does not exist, such as `31/02/2026` or `2026-02-30`, it raises ValueError.

Where this shows:
- `deliveries/dates.py:7`: the docstring said "or None if text is not a valid date". I corrected it to describe both cases: None for no recognised shape, ValueError for a non-existent day.
- `deliveries/formats.py:19`: `date(...)` raises ValueError for impossible days. The probe showed `31/02/2026` and `2026-02-30` both raise ValueError, while `tbc` and blank input return None.
- `deliveries/importer.py:18-21` and `tests/test_importer.py:9-13` depend on that ValueError: `read_orders` catches it to record skipped rows. I left `parse_date` unchanged so that behaviour stays the same.

What changed:
- `deliveries/cli.py`: `main` now catches ValueError from `parse_date` and treats it the same as None. When the date is None or invalid, it prints `invalid date` to stderr and returns 2, so `sys.exit(main())` exits with status 2. Valid dates print the delivery date and exit 0, as before.
- `tests/test_cli.py` (new): covers a valid date, `tbc`, and `31/02/2026`, checking exit status, stdout and stderr.

Verification: `python -B -m unittest discover -s tests -t .` ran 8 tests, all passing. Manual runs: `2026-03-14` printed `2026-03-17` with exit 0; `tbc` and `31/02/2026` each printed `invalid date` to stderr with exit 2. No bytecode caches were left behind.
