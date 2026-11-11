I retired `docs/ingest.md`. Every claim on it was already stated by the code, so I added no comments and changed no code. The page is deleted, and nothing was kept because no kept claims remained.

Fate list, in page order:

1. `read_rows(path)` opens a supplier CSV file and returns its rows as dictionaries keyed by the header row. **Dropped.** The `read_rows` docstring and body in `ingest/rows.py` say it (`csv.DictReader`), and `test_read_rows_uses_the_header` covers it.
2. `is_blank(row)` is true when every value is empty or only whitespace. **Dropped.** The `is_blank` body in `ingest/rows.py` says it (`all(not (value or "").strip() ...)`).
3. `parse_price(text)` turns "12.50" into 1250 cents. **Dropped.** The `parse_price` docstring in `ingest/rows.py` says it, and `test_parse_price_accepts_dot_and_comma` covers it.
4. A comma also works as the decimal separator, so "12,50" gives the same result. **Dropped.** The `parse_price` docstring says it ("12,50"), and the body does `.replace(",", ".")`.
5. `clean(rows)` removes blank rows. **Dropped.** The `clean` docstring ("Drop blank rows") says it, and `test_clean_drops_blank_rows` covers it.
6. `clean(rows)` replaces each row's price with its value in cents. **Dropped.** The `clean` docstring ("convert each price to cents") says it.
7. The module only uses the standard library's `csv` module. **Dropped.** The only import in `ingest/rows.py` is `csv`. This describes what the code is, and the page gives no rule or reason for it, so I did not turn it into a constraint comment.

Nothing was moved or not migrated. The code agrees with every claim.

Other files stating these facts: none. `README.md` and `docs/deploy.md` do not repeat any of them.

Files linking to the page: none. I found no reference to `docs/ingest.md` in the other input files.

Gaps: none.
