The deliveries CLI now checks the result of `parse_date`. When the date is not valid, it prints `invalid date` to stderr and exits with status 2. Valid dates behave as before.

Changes:
- `deliveries/cli.py`: after `parse_date(argv[0])`, a `None` result prints `invalid date` to stderr and returns 2 (`sys.exit(main())` passes that through as the exit status).
- `tests/test_cli.py` (new): one test checks that a valid date prints the delivery date with status 0, and one checks that `tbc` gives `invalid date` on stderr, nothing on stdout, and status 2.

Checks: `python -m unittest discover -s tests -t .` runs 7 tests, all passing. `python -m deliveries.cli tbc` prints `invalid date` and exits 2. `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.

Nothing was committed, and no git or task tracking was used. No existing comment became false, so none were changed.
