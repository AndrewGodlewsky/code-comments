I deleted docs/ingest.md. Every claim on it is already stated by the code, so nothing needed to move into a comment and no source file changed.

Fate list, in page order:

1. `read_rows(path)` opens a supplier CSV and returns rows as dicts keyed by the header row. Dropped. The `read_rows` docstring in ingest/rows.py says it, and `csv.DictReader` plus `test_read_rows_uses_the_header` confirm it.
2. `is_blank(row)` is true when every value is empty or only whitespace. Dropped. The name and the body (`all(not (value or "").strip() ...)`) in ingest/rows.py say it, and `test_clean_drops_blank_rows` covers it.
3. `parse_price(text)` turns "12.50" into 1250 cents. Dropped. The `parse_price` docstring and body say it, and `test_parse_price_accepts_dot_and_comma` covers it.
4. A comma also works as the decimal separator, so "12,50" gives the same result. Dropped. The docstring says 'Accepts "12.50" and "12,50"', the `.replace(",", ".")` shows it, and the test covers it.
5. `clean(rows)` removes blank rows and replaces each price with cents. Dropped. The `clean` docstring says it, and `test_clean_drops_blank_rows` covers it.
6. The module only uses the standard library's `csv` module. Dropped. The only import in ingest/rows.py is `import csv`.

Nothing was moved, kept or left unmigrated, and the code contradicts none of the claims.

Other files:
- No file links to docs/ingest.md. README.md and docs/deploy.md do not mention it.
- No other file states these facts.
- There are no gaps.
- The page held no kept claims, so I deleted it entirely.
- docs/deploy.md is untouched.
