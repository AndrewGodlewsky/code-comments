I retired docs/ingest.md. Every claim on it has a fate below. The page is deleted because no kept claim remained. The only code change is one comment in ingest/rows.py. The three unit tests pass.

Fate list, in page order:

1. "`read_rows(path)` opens a supplier CSV file and returns its rows as dictionaries, keyed by the column names in the header row." Dropped. ingest/rows.py read_rows docstring already states it, and the body uses csv.DictReader.
2. "`is_blank(row)` is true when every value in the row is empty or only whitespace." Dropped. ingest/rows.py is_blank body (`all(not (value or "").strip() ...)`) states it.
3. "`parse_price(text)` turns a price such as "12.50" into 1250 cents." Dropped. ingest/rows.py parse_price docstring states it.
4. "A comma also works as the decimal separator, so "12,50" gives the same result." Dropped. parse_price docstring ("Accepts "12.50" and "12,50"") and the `.replace(",", ".")` call state it; tests/test_rows.py test_parse_price_accepts_dot_and_comma covers it.
5. "`clean(rows)` removes blank rows and replaces each row's price with its value in cents." Dropped. ingest/rows.py clean docstring and body state it.
6. "The module only uses the standard library's `csv` module." Moved to ingest/rows.py, comment above `import csv`: "Standard library only: this module takes no third-party dependencies." Evidence: the only import in rows.py is `import csv`. The page states this as a constraint on future edits, which the code does not show, so I moved it rather than dropping it.

Other files: none state the moved fact outside the page. No file links to docs/ingest.md or to any section I removed. tests/test_rows.py imports ingest.rows, which is unaffected.

Gaps for you:
- Claim 6 is a policy. If the stdlib-only rule is no longer intended, delete that comment.
- docs/ingest.md held no kept claims. I did not move the module overview (title and "Ingest") anywhere, because it carried no content beyond the claims above. If you want a module overview, the ingest/rows.py module docstring is the natural place.
- docs/deploy.md is unchanged and still exists.
