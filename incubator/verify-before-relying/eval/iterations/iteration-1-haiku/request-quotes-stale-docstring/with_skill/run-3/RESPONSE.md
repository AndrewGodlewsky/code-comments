The premise is partly wrong. parse_date does not return None for every invalid date. Its docstring at deliveries/dates.py:7 says it returns None "if text is not a valid date", but the code only returns None when the text fits no date shape (for example "tbc" or blank text). When the text has a date shape but the date does not exist, such as 31/02/2026, read_date (deliveries/formats.py:19) calls date(...), which raises ValueError. Before this change, the CLI crashed on "tbc" with a TypeError (None + timedelta) and on "31/02/2026" with a traceback. The importer already relies on this: deliveries/importer.py:78 catches ValueError for nonexistent dates.

What I did:
- deliveries/dates.py: corrected the parse_date docstring to describe the real behaviour (None for text in no date shape, ValueError for a shape that is not a real date). Code unchanged.
- deliveries/cli.py: if parse_date returns None or raises ValueError, the CLI prints "invalid date" to stderr and returns status 2, so sys.exit gives 2. Valid dates behave as before.
- tests/test_cli.py: new tests for a valid date, "tbc" (exit 2), and "31/02/2026" (exit 2).

Checks: all 8 tests pass (python -B -m unittest discover -s tests -t .). Manual runs: "tbc" and "31/02/2026" print "invalid date" to stderr and exit 2; "2026-03-14" prints 2026-03-17 and exits 0.

I treated 31/02/2026 as a mistyped date that should get the same clear error as "tbc", since that is what the request wants. If you want the ValueError to propagate instead, drop the except clause in cli.py.
