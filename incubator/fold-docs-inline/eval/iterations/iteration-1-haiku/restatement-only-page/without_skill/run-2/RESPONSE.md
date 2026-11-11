I retired docs/ingest.md. Most of it already lived in the code, so only one small addition was needed.

What I did:
- Checked each section against ingest/rows.py. `read_rows`, `parse_price` (including the comma separator) and `clean` already have docstrings that say what the page said.
- `is_blank` had no docstring, so I added one in ingest/rows.py: "Return True when every value in the row is empty or only whitespace."
- The page's note that the module only uses the standard library's `csv` module is visible from the import at the top of ingest/rows.py, so I did not copy it anywhere.
- Deleted docs/ingest.md. Nothing in the repository links to it (README.md and docs/deploy.md do not reference it).
- docs/deploy.md is unrelated to ingest and is unchanged.
- Ran the unit tests (python -m unittest discover): 3 tests, all pass.
