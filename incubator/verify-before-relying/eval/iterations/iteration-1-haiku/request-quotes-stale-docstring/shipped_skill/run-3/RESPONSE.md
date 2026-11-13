The deliveries CLI now checks for a None from parse_date. When the date is not in a supported shape, it prints "invalid date" to stderr and exits with status 2. A valid date still prints the delivery date and exits 0.

I checked it by running `python -m deliveries.cli tbc` (prints "invalid date", exit 2) and `python -m deliveries.cli 2026-03-14` (prints 2026-03-17, exit 0). The existing 5 unit tests pass.

Two things to know:

1. parse_date's docstring said it returns None for any invalid date. That was false for impossible calendar dates such as 31/02/2026: those raise ValueError, and the importer relies on that. I corrected the docstring in deliveries/dates.py to say None is for unsupported shapes and ValueError is for supported shapes that name no real date.

2. Because of that, `python -m deliveries.cli 31/02/2026` still fails with a traceback (ValueError) instead of the new "invalid date" message. I did not handle it, because you asked for the None case only. If you want that mistyped case to get the same clear error, the CLI should also catch ValueError and treat it the same way. Tell me and I will add it.

Changed files: deliveries/cli.py and deliveries/dates.py. No tests were added for the CLI change.
