The deliveries CLI now checks for an invalid date. When `parse_date` returns `None`, `main` prints `invalid date` to stderr and returns exit status 2. A valid date still prints the delivery date and exits 0.

Changes:
- `deliveries/cli.py`: added the `None` check before `delivery_date` is called. Before this change, a bad date raised a `TypeError` traceback instead.
- `tests/test_cli.py` (new): covers the invalid-date path (stderr message, status 2, nothing on stdout) and a valid date (`2026-03-14` gives `2026-03-17`).

Checks: `python -m unittest discover -s tests -t .` runs 7 tests, all passing. `python -m deliveries.cli 31/02/2026` prints `invalid date` and exits 2. `python -m deliveries.cli 14/03/2026` prints `2026-03-17` and exits 0.

Your claim about `parse_date` holds: its docstring says it returns None for text that is not a valid date, and the code does that. No existing comment was made false by this change, so I left all comments as they were. I did not add a comment, since the change is routine.

Not changed: running `python -m deliveries.cli` with no argument still raises an `IndexError` from `argv[0]`. You did not ask about that, so I left it alone.
