The deliveries CLI now checks the result of `parse_date`. If it gets `None` back, it prints "invalid date" to stderr and exits with status 2. The change is in `deliveries/cli.py`.

I checked the docstring claim before relying on it. `parse_date` does return `None` for blank text, non-date text such as "tbc", and dates that don't exist such as 2026-02-30 and 31/02/2026. I ran the CLI with 2026-02-30, which printed "invalid date" and exited 2. A valid date, 2026-03-14, still prints the delivery date and exits 0.

I didn't add a test for the CLI, and I didn't run the existing test suite. The CLI still reads only the first argument, so running it with no argument will still raise an IndexError. I left that alone because it wasn't part of the request.
