The premise checks out. `parse_date` (deliveries/dates.py:7) says it returns None when text is not a valid date. It does: it delegates to `read_date` (deliveries/formats.py:13), which returns None when no shape fits or the date does not exist (for example 31/02/2026). tests/test_dates.py pins the blank and "tbc" cases, so I built on this claim as written and did not change the docstring.

The deliveries CLI (deliveries/cli.py) now checks for None. When `parse_date` returns None, `main` prints "invalid date" to stderr and returns 2, so `sys.exit(main())` exits with status 2. Before this change, a mistyped date crashed with a TypeError from `delivery_date`.

Checks run:
- `python -B -m unittest discover -s tests -t .`: 5 tests, all pass.
- `python -B -m deliveries.cli 2026-03-14`: prints 2026-03-17, exit 0.
- `python -B -m deliveries.cli 31/02/2026`: stderr "invalid date", exit 2.
- `python -B -m deliveries.cli tbc`: stderr "invalid date", exit 2.

No new tests were added, and no __pycache__ files were left behind. Only deliveries/cli.py was changed, plus this RESPONSE.md.
