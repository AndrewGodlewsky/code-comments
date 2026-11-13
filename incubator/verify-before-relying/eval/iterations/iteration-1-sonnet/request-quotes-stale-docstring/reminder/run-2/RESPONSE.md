The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when the date can't be used. I added tests/test_cli.py for this, and the full test suite passes.

The `parse_date` docstring was wrong, so I checked it against the code and tests before relying on it. It says `parse_date` returns None for anything that isn't a valid date. That is only true for text not in a recognised format, such as blank text or "tbc". A well-formed date that doesn't exist, such as 31/02/2026, raises ValueError. `tests/test_importer.py` relies on that, and `read_orders` catches it. A CLI that only checked for None would have crashed with a traceback on that typo.

- **CLI** (`deliveries/cli.py`): it handles both outcomes. A None result and a ValueError both print "invalid date" and exit 2.
- **Docstring** (`deliveries/dates.py`): I corrected it to say None for unrecognised text and ValueError for a nonexistent date.

There was no stated requirement or outside fact in conflict with this. The only conflict was the docstring against the code and tests, and I resolved it in favour of the code. I left the importer as it was.

One thing I didn't change: running the CLI with no argument still raises IndexError.
