I've retired docs/ingest.md and deleted it. Its content now lives in the code.

What I did with each part of the page:

- `read_rows(path)`: already covered by the function docstring in `ingest/rows.py`, so nothing moved.
- `is_blank(row)`: the function had no docstring. I added one: "Return True when every value in the row is empty or only whitespace."
- `parse_price(text)`: already covered by its docstring, which includes both the dot and comma separators. Nothing moved.
- `clean(rows)`: already covered by its docstring. Nothing moved.
- "The module only uses the standard library's csv module.": I added this to the module docstring in `ingest/rows.py`.

Nothing else referenced docs/ingest.md, so no links needed updating. docs/deploy.md is unchanged and still in place.

The tests in tests/test_rows.py pass (3 tests). I did not add tests for is_blank, since this change was documentation only.
