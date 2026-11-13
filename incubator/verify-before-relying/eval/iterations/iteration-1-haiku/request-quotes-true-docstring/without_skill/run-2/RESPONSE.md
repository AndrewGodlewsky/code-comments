I added the check to the deliveries CLI. In `deliveries/cli.py`, `main()` now calls `parse_date` on the argument; if the result is `None`, it prints `invalid date` to stderr and returns 2, so `sys.exit(main())` exits with status 2. Valid dates behave as before.

I ran the existing unit tests (5 pass) and checked the CLI by hand:
- `2026-03-14` prints `2026-03-17` and exits 0.
- `tbc` prints `invalid date` to stderr and exits 2.
- `31/02/2026` (a date that does not exist) prints `invalid date` to stderr and exits 2.

I did not add a test for the new CLI branch.
