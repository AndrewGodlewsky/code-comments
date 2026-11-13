I added the check to the deliveries CLI. In `deliveries/cli.py`, `main` now prints `invalid date` to stderr and returns status 2 when `parse_date` returns `None`. Before this, a mistyped date crashed with a `TypeError` from `delivery_date`.

Checks run:
- `2026-03-14` prints `2026-03-17` and exits 0.
- `31/02/2026` prints `invalid date` to stderr and exits 2.
- `tbc` prints `invalid date` to stderr and exits 2.
- The existing unit tests pass (5 tests).

No comments were added or changed. The `parse_date` docstring already matches its behaviour, and the change needed no new rationale.

Not changed: running the CLI with no arguments still raises an `IndexError` on `argv[0]`. That is outside this request, so I left it alone.
