I deleted docs/ingest.md and made no code changes, because nothing on it needed to move.

Each statement on the page was either already in the code or only restated it:

- read_rows(path): the docstring in ingest/rows.py already says it returns each data row as a dict keyed by the header row.
- is_blank(row): the page restates the function body. Adding a docstring would only repeat the code.
- parse_price(text): the docstring already covers the cents result and the comma decimal separator, and tests/test_rows.py checks both.
- clean(rows): the docstring already covers dropping blank rows and converting prices to cents.
- "The module only uses the standard library's csv module": this is visible from the imports. I found no recorded reason for it in the request, tests or other docs, so I did not add it to the code.

No other file referenced docs/ingest.md, so nothing else needed updating. docs/deploy.md and README.md are unchanged. docs/deploy.md is not part of the retiring page.
