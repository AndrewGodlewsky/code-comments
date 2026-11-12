The deliveries CLI now checks the result of `parse_date`. When it returns `None`, the CLI prints `invalid date` to stderr and exits with status 2. The change is in `deliveries/cli.py`:

```python
ordered = parse_date(argv[0])
if ordered is None:
    print("invalid date", file=sys.stderr)
    return 2
```

Before the change, a mistyped date such as `2026-02-31` or `tomorrow` crashed with a `TypeError` traceback and exit status 1. Now `python -m deliveries.cli 2026-02-31` and `python -m deliveries.cli tomorrow` each print `invalid date` and exit with 2. A valid date such as `14/03/2026` still prints `2026-03-17` and exits 0. The existing unit tests pass (5 tests).

I did not add a test for the CLI path. I can add one if you want it covered.

Separately, running the CLI with no argument still raises an IndexError on `argv[0]`. I left that alone because it was outside this request.
