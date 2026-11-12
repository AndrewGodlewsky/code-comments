The deliveries CLI now prints `invalid date` to stderr and exits with status 2 when the date is not usable.

One claim in your request was only partly right. parse_date returns None only when the text is not in a date shape (for example "tbc" or a blank string). When the text has a date shape but the date does not exist, such as 31/02/2026, parse_date raises ValueError instead of returning None. Before this change the CLI crashed on None with a TypeError, and on 31/02/2026 it crashed with an uncaught ValueError.

What I changed:
- deliveries/cli.py: main() treats both None and ValueError from parse_date as an invalid date. It prints `invalid date` to stderr and returns 2. A valid date still prints the delivery date and returns 0.
- deliveries/dates.py: the parse_date docstring said it returns None for any invalid date, which was false. It now says None means the shape is not accepted, and that ValueError is raised for a well-shaped date that does not exist.
- tests/test_cli.py (new): covers a valid date, a note ("tbc") and an impossible date (31/02/2026).
- tests/test_dates.py: added a test that 31/02/2026 raises ValueError.

I did not make parse_date return None for impossible dates. deliveries/importer.py catches ValueError to list such rows as typos in its skipped list, and tests/test_importer.py checks that. Changing parse_date would have silently dropped those rows.

Verification: `python -m unittest discover -s tests -t .` runs 9 tests, all passing. Manual runs: `tbc` and `31/02/2026` each print `invalid date` and exit 2; `2026-03-14` prints `2026-03-17` and exits 0.

Not committed: this run did not use git.
