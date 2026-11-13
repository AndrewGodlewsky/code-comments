The deliveries CLI now checks for an invalid date. When `parse_date` returns `None`, `main` prints `invalid date` to stderr and returns status 2, so `sys.exit(main())` exits with 2. Valid dates behave as before.

Changes:
- `deliveries/cli.py`: added the `None` check after `parse_date(argv[0])`.
- `tests/test_cli.py` (new): covers the invalid-date path (message on stderr, status 2, nothing on stdout) and a valid date (status 0, delivery date printed).

Verification: `python -m unittest discover -s tests -t .` ran 7 tests, all passing. `python -m deliveries.cli tbc` printed `invalid date` and exited with 2.

Not changed: running the CLI with no argument still raises an IndexError, as it did before. This was outside the request.
