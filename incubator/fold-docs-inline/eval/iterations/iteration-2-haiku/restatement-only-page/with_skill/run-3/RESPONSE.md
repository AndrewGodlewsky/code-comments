I retired `docs/ingest.md` and changed nothing else. Every claim on the page was already stated by the code or its docstrings, so no comments were added and no code changed.

Fate list, in page order:

1. "`read_rows(path)` opens a supplier CSV file and returns its rows as dictionaries, keyed by the column names in the header row." - Dropped. `ingest/rows.py` lines 6-9 open the file and use `csv.DictReader`, and the docstring on line 7 says the same. `tests/test_rows.py` lines 18-23 check the header keys.
2. "`is_blank(row)` is true when every value in the row is empty or only whitespace." - Dropped. `ingest/rows.py` lines 12-13 (`all(not (value or "").strip() ...)`) state it.
3. "`parse_price(text)` turns a price such as "12.50" into 1250 cents." - Dropped. `ingest/rows.py` line 17 docstring ("Return the price in cents. Accepts "12.50" and "12,50".") and the code on lines 18-19; `tests/test_rows.py` line 10.
4. "A comma also works as the decimal separator, so "12,50" gives the same result." - Dropped. `ingest/rows.py` line 17 docstring, line 18 (`.replace(",", ".")`); `tests/test_rows.py` line 11.
5. "`clean(rows)` removes blank rows and replaces each row's price with its value in cents." - Dropped. `ingest/rows.py` line 23 docstring and lines 24; `tests/test_rows.py` lines 14-16.
6. "The module only uses the standard library's `csv` module." - Dropped. `ingest/rows.py` line 3 (`import csv`) is the only import in `ingest/`, and `ingest/__init__.py` is empty. The page gives no rule or reason, so this is a description the code already shows.

Not migrated: none. Every value on the page matches the code.
Kept: none. The page held no operational steps, product intent or cross-module overview, so nothing needed a home in a document.

Other files: `README.md`, `docs/deploy.md`, `ingest/`, and `tests/` are unchanged. No file links to `docs/ingest.md` or to any section of it, and no moved fact needs reconciling in another file.

Gaps: none. `docs/deploy.md` was not on the retired page and was left as is.
