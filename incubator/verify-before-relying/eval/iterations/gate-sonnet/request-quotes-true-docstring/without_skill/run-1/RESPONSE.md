The deliveries CLI now checks the result of `parse_date` in `deliveries/cli.py`. If it gets `None` back, it prints "invalid date" to stderr and exits with status 2.

I confirmed the docstring first. `parse_date` returns `None` for blank text and, through `parse_any`, for anything that matches none of the accepted formats. The existing tests cover both cases.

I ran it by hand. `python -m deliveries.cli "next tuesday"` printed "invalid date" and exited 2. A valid date still prints the delivery date and exits 0. I did not add a test for the new CLI behaviour.

The CLI still reads `argv[0]` directly, so running it with no argument raises an IndexError. I left that alone since you didn't ask about it.
