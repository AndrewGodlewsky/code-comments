I changed `deliveries/cli.py` so that `main` checks the result of `parse_date`. When it gets None, it prints "invalid date" to stderr and returns status 2, which `sys.exit(main())` passes on as the exit code. Before this change, a mistyped date crashed with a TypeError from `delivery_date`. Valid dates behave as before.

Checks: the existing 5 unit tests pass. `python -m deliveries.cli tbc` prints "invalid date" to stderr and exits 2. `python -m deliveries.cli 14/03/2026` prints 2026-03-17 and exits 0.

No comments were added or changed. The `parse_date` docstring is still accurate, and the change needed no new explanation. No tests were added for the new branch; say if you want one.
