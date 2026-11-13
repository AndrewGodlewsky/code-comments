I changed `main` in `deliveries/cli.py` so that when `parse_date` returns `None`, it prints `invalid date` to stderr and returns status 2. `sys.exit(main())` turns that into exit status 2 from the command line.

```python
ordered = parse_date(argv[0])
if ordered is None:
    print("invalid date", file=sys.stderr)
    return 2
```

Checks run:
- `python -m deliveries.cli 2026-03-14` prints `2026-03-17` and exits 0.
- `python -m deliveries.cli tbc` prints `invalid date` to stderr and exits 2.
- `python -m unittest discover -s tests -t .` runs 5 tests, all passing.

Nothing else changed. The module docstring and the `parse_date` docstring are still accurate, so no comment edits were needed. I did not add a CLI test, since the request was only for the behaviour change.
