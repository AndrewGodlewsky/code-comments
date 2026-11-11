I added the check to the deliveries CLI in `deliveries/cli.py`. After `parse_date` runs, `main` now tests whether the result is `None`. If it is, the CLI prints `invalid date` to stderr and returns exit status 2 without calling `delivery_date`. Valid dates behave as before.

I checked it by hand: `python -m deliveries.cli tbc` prints `invalid date` and exits with 2, and `python -m deliveries.cli 2026-03-14` still prints `2026-03-17` and exits 0. The existing unit tests (5) pass.
