I changed `main` in `deliveries/cli.py`. When `parse_date` returns None, the CLI now prints "invalid date" to stderr and returns 2, so `sys.exit(main())` exits with status 2. Valid dates print the delivery date and exit 0 as before.

Checked by running the CLI:
- `2026-03-14` prints `2026-03-17` and exits 0.
- `31/02/2026` prints "invalid date" to stderr and exits 2.
- `tbc` prints "invalid date" to stderr and exits 2.

The existing unit tests (5) pass. I added no comment: the change is routine, and the module and `parse_date` docstrings are still accurate.
