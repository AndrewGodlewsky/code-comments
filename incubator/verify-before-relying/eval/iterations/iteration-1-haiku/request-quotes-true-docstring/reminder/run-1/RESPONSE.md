The deliveries CLI now checks for an invalid date. When `parse_date` returns None, `python -m deliveries.cli` prints `invalid date` to stderr and exits with status 2. Valid dates behave as before.

Before relying on the docstrings, I checked them against the code and tests. `parse_date` says it returns None when text is not a valid date. That holds: `read_date` returns None for text that matches no format and for dates that do not exist, and `test_a_note_instead_of_a_date_is_none` covers the first case. The module and `read_orders` docstrings also match the code, so I corrected nothing and found no conflict with your request.

Changes, all in the outputs repository:
- `deliveries/cli.py`: after `parse_date`, a None result prints `invalid date` to stderr and returns 2. Before this change, a bad date reached `delivery_date` and crashed with a TypeError.
- `tests/test_cli.py` (new): one test checks that a valid date prints the delivery date and returns 0. The other checks that `31/02/2026` prints `invalid date` to stderr, prints nothing to stdout, and returns 2.

Verification: `python -m unittest discover -s tests -t .` runs 7 tests, all passing. `python -m deliveries.cli tbc` prints `invalid date` and exits 2. `python -m deliveries.cli 14/03/2026` prints `2026-03-17` and exits 0.

Not changed: running the CLI with no argument still fails with an IndexError on `argv[0]`. You did not ask for that, so I left it alone. It could be handled the same way if you want it.
