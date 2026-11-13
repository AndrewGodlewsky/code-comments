The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date argument is not usable. Valid dates behave as before.

One thing differed from the docstring. parse_date does not return None for every invalid date. Text in a known shape that names a date that does not exist, such as 31/02/2026 or 2026-02-30, raises ValueError. Blank text and text in no known shape, such as "tbc", return None. The importer already relies on that ValueError to skip such rows. Because the CLI would otherwise crash on those inputs with a traceback, it treats ValueError the same as None.

Changes, all in the outputs repository:
- deliveries/cli.py: main() catches ValueError from parse_date, and when the result is None it prints "invalid date" to stderr and returns 2.
- deliveries/dates.py: the parse_date docstring now says it returns None for blank or unrecognised text and raises ValueError for a well-formed but nonexistent date. The old wording ("None if text is not a valid date") was wrong for impossible dates.
- tests/test_cli.py: new tests for a valid date (prints 2026-03-17, exit 0), "tbc", blank input and 31/02/2026 (each prints "invalid date", exit 2).

Verification: python -m unittest discover -s tests -t . runs 9 tests, all passing. Running python -m deliveries.cli tbc and 31/02/2026 exits with status 2 and the message. Running it with 14/03/2026 prints 2026-03-17.

Conflict to note: your request said the CLI should act when parse_date returns None. Handling only None would leave impossible dates crashing with a traceback, so I also covered the ValueError case. If you would rather parse_date return None for impossible dates too, the importer's skipped-row handling would need to change with it.

Not changed: running the CLI with no argument still raises IndexError. That was outside this request.
