I retired docs/ingest.md and moved what belonged beside the code.

What was on the page:
- read_rows, parse_price and clean were already documented by their docstrings in ingest/rows.py, and the comma decimal rule is covered there and by tests/test_rows.py. Nothing needed to move for these.
- is_blank had no docstring, so its behaviour (True when every value is empty or whitespace) now lives on the function in ingest/rows.py.
- The note that the module uses only the standard library's csv module now sits in the module docstring of ingest/rows.py.

Changes:
- ingest/rows.py: added the is_blank docstring and extended the module docstring.
- docs/ingest.md: deleted.

Nothing else referred to docs/ingest.md (checked README.md and docs/deploy.md), so no links needed updating. docs/deploy.md is unchanged. The unit tests pass (3 tests, OK).
