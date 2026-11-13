I retired docs/ingest.md and deleted it. Nothing needed to move into the code, so no source file changed.

Fate list, in page order:

1. `read_rows(path)` opens a supplier CSV and returns rows as dicts keyed by the header row. Dropped. The `read_rows` docstring in ingest/rows.py says it, and `csv.DictReader` and `test_read_rows_uses_the_header` show it.
2. `is_blank(row)` is true when every value is empty or only whitespace. Dropped. The body of `is_blank` in ingest/rows.py shows it.
3. `parse_price(text)` turns a price such as "12.50" into 1250 cents. Dropped. The `parse_price` docstring and `test_parse_price_accepts_dot_and_comma` state it.
4. A comma also works as the decimal separator, so "12,50" gives the same result. Dropped. The `parse_price` docstring says it accepts "12.50" and "12,50", and the code replaces "," with ".".
5. `clean(rows)` removes blank rows. Dropped. The `clean` docstring says "Drop blank rows", and `test_clean_drops_blank_rows` covers it.
6. `clean(rows)` replaces each row's price with its value in cents. Dropped. The `clean` docstring says "convert each price to cents".
7. The module only uses the standard library's `csv` module. Dropped. The only import in ingest/rows.py is `import csv`. The page gave no reason or rule for it, so I did not turn it into a constraint comment.

Other files:
- No other file states these facts. README.md and docs/deploy.md do not link to docs/ingest.md.
- There are no gaps and no claims the code contradicts.
- The page held no kept claims, so deleting it was safe. docs/deploy.md is untouched.
