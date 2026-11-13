I changed `main` in `deliveries/cli.py`. When `parse_date` returns `None`, the CLI now prints `invalid date` to stderr and returns status 2, so `sys.exit(main())` exits with 2. Valid dates print the delivery date and exit 0 as before.

```python
ordered = parse_date(argv[0])
if ordered is None:
    print("invalid date", file=sys.stderr)
    return 2
```

Checks run in the repository:
- `python -m deliveries.cli tbc` prints `invalid date` to stderr and exits 2.
- `python -m deliveries.cli 31/02/2026` prints `invalid date` and exits 2.
- `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.
- `python -m unittest discover -s tests -t .` passes all 5 tests.

Comments: I checked the comments near the change. None became false, so I left them alone. I added no new comment, since this is a routine change. The `Usage` docstring in `cli.py` does not list exit codes; I did not add them because nothing in the request asked for that.

I did not add a test for the new branch, since you asked only for the CLI change.
