I retired docs/ingest.md. Every claim on it was already stated by the code, so nothing moved into comments, and I deleted the page. No source, test or other doc changed.

Fate list, in page order:

1. "`read_rows(path)` opens a supplier CSV file and returns its rows as dictionaries, keyed by the column names in the header row." Dropped. ingest/rows.py:6-9 does this, and its docstring (line 7) says it. tests/test_rows.py:18-23 checks the header keying.
2. "`is_blank(row)` is true when every value in the row is empty or only whitespace." Dropped. ingest/rows.py:12-13 (`all(not (value or "").strip() ...)`).
3. "`parse_price(text)` turns a price such as "12.50" into 1250 cents." Dropped. ingest/rows.py:16-19, docstring at line 17; tests/test_rows.py:9-12.
4. "A comma also works as the decimal separator, so "12,50" gives the same result." Dropped. ingest/rows.py:17 docstring (`Accepts "12.50" and "12,50"`) and line 18 (`replace(",", ".")`); tests/test_rows.py:11.
5. "`clean(rows)` removes blank rows and replaces each row's price with its value in cents." Dropped. ingest/rows.py:22-24, docstring at line 23; tests/test_rows.py:14-16.
6. "The module only uses the standard library's `csv` module." Dropped. ingest/rows.py:3 `import csv` is the module's only import. This is a judgment call: it is a negative constraint a later editor could break by adding a dependency. The page does not state it as a rule or give a reason, so I did not add it as a comment. If you want it kept, I can add it to the module docstring of ingest/rows.py.

The heading "Ingest" is not a claim.

Other files that state a moved fact: none, since nothing was moved.

Files that link to the page or to a removed section: none. A search of the repository found no reference to docs/ingest.md. tests/test_rows.py imports ingest.rows, which is code, not the page.

Gaps: none that block the retirement. No claim remained, so the page is deleted. docs/deploy.md is untouched.
