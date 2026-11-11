I retired docs/ingest.md. Every claim on it is already stated by the code, so nothing moved into comments and no code or tests changed. The page is deleted; docs/deploy.md was left alone.

Fate list, in page order:

1. "`read_rows(path)` opens a supplier CSV file and returns its rows as dictionaries, keyed by the column names in the header row." Dropped. ingest/rows.py:7 docstring says "Return each data row of the CSV file at path as a dict keyed by the header row."; the body (line 9) uses csv.DictReader.
2. "`is_blank(row)` is true when every value in the row is empty or only whitespace." Dropped. ingest/rows.py:13 `all(not (value or "").strip() for value in row.values())`.
3. "`parse_price(text)` turns a price such as "12.50" into 1250 cents." Dropped. ingest/rows.py:17 docstring and line 18-19 body; tests/test_rows.py:10 asserts parse_price("12.50") == 1250.
4. "A comma also works as the decimal separator, so "12,50" gives the same result." Dropped. ingest/rows.py:17 docstring says 'Accepts "12.50" and "12,50"'; line 18 replaces "," with "."; tests/test_rows.py:11.
5. "`clean(rows)` removes blank rows and replaces each row's price with its value in cents." Dropped. ingest/rows.py:23 docstring "Drop blank rows and convert each price to cents."; line 24 body; tests/test_rows.py:14-16.
6. "The module only uses the standard library's `csv` module." Dropped. ingest/rows.py:3 `import csv` is the only import, and ingest/__init__.py is empty. This is the closest call: it reads as a constraint, but the import list shows it completely. If you want a guard against adding third-party dependencies, that is a policy to record somewhere else, and I did not invent a comment for it.
7. The "# Ingest" heading. No claim; removed with the page.

Kept claims: none, so docs/ingest.md is deleted. No comments were added.

Not migrated: none. Every claim matches the code.

Other files: no file in the repository mentions docs/ingest.md or a section of it (grep for "ingest" finds only tests/test_rows.py importing the ingest package). Nothing else states a moved fact, so there is nothing to reconcile.

Gaps: none. docs/deploy.md is outside this request and is unchanged. It holds operational content (the etl-2 Monday 07:00 schedule and the 06:00 upload deadline), which would be kept as written if it were ever retired.
