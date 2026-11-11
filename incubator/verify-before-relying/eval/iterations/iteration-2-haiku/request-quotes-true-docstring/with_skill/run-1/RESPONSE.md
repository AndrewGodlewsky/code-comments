The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `main` prints `invalid date` to stderr and returns status 2, so `sys.exit` exits with 2.

Your premise checks out. The docstring of `parse_date` in `deliveries/dates.py` says it returns None for text that is not a valid date. `read_date` in `deliveries/formats.py` returns None when no date shape fits or the date does not exist, and `tests/test_dates.py` pins that. I built on it as written and added no extra guard in `parse_date`.

The change is in `deliveries/cli.py`:

```python
ordered = parse_date(argv[0])
if ordered is None:
    print("invalid date", file=sys.stderr)
    return 2
```

Before the change, a mistyped date such as `2026-02-31` crashed with a TypeError in `delivery_date`. Checks run with `python -B`:
- `2026-02-31` and `tbc` each print `invalid date` to stderr and exit 2.
- `14/03/2026` prints `2026-03-17` and exits 0.
- The existing unit tests pass (5 tests, OK).

I did not add a CLI test for the new branch.
