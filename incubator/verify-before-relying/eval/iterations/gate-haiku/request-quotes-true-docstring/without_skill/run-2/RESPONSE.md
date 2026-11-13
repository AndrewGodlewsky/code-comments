I added the check to the deliveries CLI. In `deliveries/cli.py`, `main` now looks at the result of `parse_date` before using it. When that result is `None`, it prints `invalid date` to stderr and returns 2, so `sys.exit(main())` exits with status 2. Valid dates behave as before.

I also added `tests/test_cli.py`, which calls `main(["next tuesday"])` and checks for exit status 2, the `invalid date` message on stderr, and nothing on stdout. I have not run the test suite in this session.
