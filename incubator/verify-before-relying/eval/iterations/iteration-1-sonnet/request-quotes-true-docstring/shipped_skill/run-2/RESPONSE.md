The deliveries CLI now checks what `parse_date` returns. If it gets `None`, it prints `invalid date` to stderr and exits with status 2. A valid date behaves as before.

Changes:
- `deliveries/cli.py`: added the `None` check in `main`, which returns 2 (`sys.exit(main())` turns that into the exit status). I also added a line to the module docstring saying what the CLI does on an invalid date, since that is part of how callers use it.
- `tests/test_cli.py` (new): one test for a valid date and one for an invalid date. The invalid-date test checks the status, the stderr text, and that nothing goes to stdout.

I ran the test suite and it passes. I left the `parse_date` docstring alone because it is accurate: it does return `None` for an invalid date.

One thing I did not change: running the CLI with no date argument still raises an `IndexError`. You didn't ask about it.
