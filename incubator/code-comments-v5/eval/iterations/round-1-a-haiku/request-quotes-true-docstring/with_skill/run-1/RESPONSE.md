The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `main` prints `invalid date` to stderr and returns 2, so `python -m deliveries.cli` exits with status 2. Valid dates behave as before.

Changes:
- `deliveries/cli.py`: added the None check before `delivery_date` is called. Without it, a mistyped date raised a TypeError.
- `tests/test_cli.py` (new): covers a valid date printing its delivery date with status 0, and an invalid date giving status 2 with `invalid date` on stderr and nothing on stdout.

Verification: `python -m unittest discover -s tests -t .` runs 7 tests, all passing. `python -m deliveries.cli tbc` prints `invalid date` and exits 2. `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.

Comments: the module docstrings in `cli.py` and `dates.py` are still accurate, so I left them unchanged. I added no new comment, since the change is routine. Nothing was committed.
