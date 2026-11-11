The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `main` prints `invalid date` to stderr and returns status 2, so `sys.exit(main())` exits 2. A valid date still prints the arrival date and exits 0.

Change: `deliveries/cli.py`, a None check after `parse_date(argv[0])`.

Test: new `tests/test_cli.py` covers a valid date (prints `2026-03-17`, status 0) and an invalid date (`tbc`: stderr `invalid date`, nothing on stdout, status 2). All 7 tests pass with `python -m unittest discover -s tests -t .`. I also ran `python -m deliveries.cli tbc` (stderr `invalid date`, exit 2) and `python -m deliveries.cli 14/03/2026` (prints `2026-03-17`, exit 0).

Docstring check: the `parse_date` docstring ("Return the date written in text, or None if text is not a valid date") matches the code and `tests/test_dates.py`. Blank text, notes like "tbc", and nonexistent dates such as 31/02/2026 all return None. No docstring needed correcting, and I found no conflict with the request.

Not changed: with no arguments at all, `main` still raises IndexError on `argv[0]`. The request covered only a None date, so I left it alone. It is a candidate for a follow-up.
