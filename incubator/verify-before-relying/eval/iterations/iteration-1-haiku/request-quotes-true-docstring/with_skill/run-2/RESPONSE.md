The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `main` prints `invalid date` to stderr and returns 2, so `sys.exit(main())` exits with status 2. Valid dates behave as before.

Change: `deliveries/cli.py`, a None check after `parse_date(argv[0])`.

I also added `tests/test_cli.py` with two cases: a valid date prints the delivery date and returns 0, and `31/02/2026` writes `invalid date` to stderr and returns 2. All 7 tests pass (`python -B -m unittest discover -s tests -t .`), and `python -B -m deliveries.cli tbc` prints `invalid date` and exits 2.

Your premise checks out. The docstring at `deliveries/dates.py:7` says `parse_date` returns None for text that is not a valid date. The body returns `read_date(...)`, which returns None when no shape fits or the date does not exist (`deliveries/formats.py:13-23`). The existing tests `test_blank_text_is_none` and `test_a_note_instead_of_a_date_is_none`, and the importer test with `31/02/2026`, pin that behaviour, so I built on it as written and added no extra guard.
