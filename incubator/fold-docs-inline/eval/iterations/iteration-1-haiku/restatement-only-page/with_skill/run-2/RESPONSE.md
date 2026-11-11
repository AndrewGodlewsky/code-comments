# docs/ingest.md retired

I checked every claim on docs/ingest.md against ingest/rows.py and tests/test_rows.py. Each one is already stated by the code, so nothing moved into comments and nothing was kept. I deleted docs/ingest.md. docs/deploy.md and the rest of the repository are unchanged.

## Fate list

1. "`read_rows(path)` opens a supplier CSV file": **dropped**. `read_rows` opens `path` with `csv`, and the module docstring says "Read supplier price files."
2. "returns its rows as dictionaries, keyed by the column names in the header row": **dropped**. The `read_rows` docstring says so, and the body uses `csv.DictReader`. `test_read_rows_uses_the_header` covers it.
3. "`is_blank(row)` is true when every value in the row is empty or only whitespace": **dropped**. The body is `all(not (value or "").strip() for value in row.values())`.
4. "`parse_price(text)` turns a price such as "12.50" into 1250 cents": **dropped**. The `parse_price` docstring says it returns cents, and `test_parse_price_accepts_dot_and_comma` checks `"12.50"` gives 1250.
5. "A comma also works as the decimal separator": **dropped**. The `parse_price` docstring says it accepts "12,50", and the body runs `replace(",", ".")`.
6. "so "12,50" gives the same result": **dropped**. Same evidence as 5; the test checks `"12,5"` gives 1250.
7. "`clean(rows)` removes blank rows": **dropped**. The `clean` docstring says "Drop blank rows", and the body filters with `is_blank`.
8. "and replaces each row's price with its value in cents": **dropped**. The `clean` docstring says "convert each price to cents", and the body sets `price=parse_price(...)`.
9. "The module only uses the standard library's `csv` module": **dropped**. `ingest/rows.py` imports only `csv`.

Moved: none. Kept: none. Not migrated: none.

## Other files

- Files that state a moved fact: none, since no fact moved.
- Files that link to docs/ingest.md or to a removed section: none. The only match for "ingest" elsewhere is `tests/test_rows.py` importing `ingest.rows`, which is a code import and not a link to the page.
- Gaps: none. The page is deleted and held no kept claims.
