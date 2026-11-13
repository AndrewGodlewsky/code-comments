I retired `docs/ingest.md`. Every claim on it was already stated by the code, so I added no comments and deleted the page. No code, tests or other docs changed.

Fate list, in page order:

1. `read_rows(path)` opens a supplier CSV and returns rows as dicts keyed by the header row. **Dropped.** The `read_rows` docstring in `ingest/rows.py` says this, and `csv.DictReader` and `test_read_rows_uses_the_header` show it.
2. `is_blank(row)` is true when every value is empty or only whitespace. **Dropped.** The name and the body (`all(not (value or "").strip() ...)`) say it, and `test_clean_drops_blank_rows` covers it.
3. `parse_price(text)` turns "12.50" into 1250 cents. **Dropped.** The `parse_price` docstring and `test_parse_price_accepts_dot_and_comma` state it.
4. A comma also works as the decimal separator, so "12,50" gives the same result. **Dropped.** The `parse_price` docstring says `Accepts "12.50" and "12,50"`, and the code does `.replace(",", ".")`.
5. `clean(rows)` removes blank rows and replaces each price with its value in cents. **Dropped.** The `clean` docstring says it, and the body does exactly that.
6. The module only uses the standard library's `csv` module. **Dropped.** The only import in `ingest/rows.py` is `import csv`, so the imports show it.

Nothing was kept, moved or not migrated, so the code does not contradict the page anywhere.

- **Other files stating a moved fact:** none, since nothing moved.
- **Links to the page:** none. `README.md` and `docs/deploy.md` do not reference `docs/ingest.md`.
- **Gaps:** none.
- **Page status:** deleted. `docs/deploy.md` stays; it covers operations and was out of scope.
