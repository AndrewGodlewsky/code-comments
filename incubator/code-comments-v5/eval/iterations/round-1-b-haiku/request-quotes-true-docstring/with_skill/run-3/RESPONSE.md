The deliveries CLI now checks for an invalid date. In `deliveries/cli.py`, `main` calls `parse_date` and, when it returns `None`, prints `invalid date` to stderr and returns 2, so `sys.exit(main())` exits with status 2.

Before the change, a mistyped date such as `2026-13-45` crashed with a `TypeError` from `delivery_date(None)`. I reproduced that first. After the change:

- `python -m deliveries.cli 2026-13-45` prints `invalid date` and exits 2.
- `python -m deliveries.cli tbc` prints `invalid date` and exits 2.
- `python -m deliveries.cli 14/03/2026` still prints `2026-03-17`.
- The existing 5 tests pass.

Your request's claim about `parse_date` holds: its docstring says it returns None for text that is not a valid date, and `read_date` and the tests confirm that. I did not change `dates.py` or `importer.py`. I added no comment, because this is a routine change and the existing module docstring still describes the CLI accurately.

One gap I did not address: running `python -m deliveries.cli` with no argument raises an `IndexError` on `argv[0]`. That is outside this request, so I left it alone.
