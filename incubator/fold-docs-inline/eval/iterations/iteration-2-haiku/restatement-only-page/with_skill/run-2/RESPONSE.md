I retired docs/ingest.md. Every claim on it was already stated by the code, so nothing needed to move into a comment, and I deleted the page.

Fate list for docs/ingest.md, in page order:

- "`read_rows(path)` opens a supplier CSV file and returns its rows as dictionaries, keyed by the column names in the header row." Dropped. Stated at ingest/rows.py `read_rows` (docstring: "Return each data row of the CSV file at path as a dict keyed by the header row."; body uses csv.DictReader).
- "`is_blank(row)` is true when every value in the row is empty or only whitespace." Dropped. Stated by the body of ingest/rows.py `is_blank`: `all(not (value or "").strip() for value in row.values())`.
- "`parse_price(text)` turns a price such as "12.50" into 1250 cents." Dropped. Stated at ingest/rows.py `parse_price` (docstring: "Return the price in cents. Accepts "12.50" and "12,50"."); tests/test_rows.py asserts `parse_price("12.50") == 1250`.
- "A comma also works as the decimal separator, so "12,50" gives the same result." Dropped. Stated by the `parse_price` docstring and by `.replace(",", ".")` in its body; tests/test_rows.py asserts `parse_price("12,5") == 1250`.
- "`clean(rows)` removes blank rows and replaces each row's price with its value in cents." Dropped. Stated at ingest/rows.py `clean` (docstring: "Drop blank rows and convert each price to cents."); tests/test_rows.py `test_clean_drops_blank_rows`.
- "The module only uses the standard library's `csv` module." Dropped. ingest/rows.py line 3 `import csv` is its only import, and no other module is imported there. This describes the code and the page gives no rule or reason, so it is not carried as a constraint.
- The "# Ingest" heading is not a claim.

Nothing was moved, so no comment or code changed. No kept claims remained, so I deleted docs/ingest.md as you asked. docs/deploy.md, README.md, the ingest package and the tests are unchanged. The docs/ folder remains because it still holds deploy.md.

Other files: no file links to docs/ingest.md or any section of it (checked README.md, docs/deploy.md and the source and test files). No other file states a moved fact, since nothing moved.

Gaps: none. Nothing was kept, so no content needs a new home.
