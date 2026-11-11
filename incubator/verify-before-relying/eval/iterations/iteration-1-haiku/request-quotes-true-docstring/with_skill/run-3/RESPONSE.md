The deliveries CLI now checks for an invalid date. When parse_date returns None, `python -m deliveries.cli` prints "invalid date" to stderr and exits with status 2 (deliveries/cli.py, in main()).

Your premise checks out. The docstring at deliveries/dates.py:7 says parse_date returns None for text that is not a valid date. The body calls read_date (deliveries/formats.py:13-23), which returns None both when no shape matches and when the date does not exist (for example 31/02/2026). The tests in tests/test_dates.py agree, so I left that docstring unchanged and built on it as written.

Verification: the 5 existing unit tests pass. A probe confirmed `2026-03-14` prints `2026-03-17` with exit 0, while `31/02/2026` and `tbc` print "invalid date" to stderr with exit 2.
