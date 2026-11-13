I deleted docs/ingest.md. Nothing had to move into the code, and no code was changed.

I checked each claim on the page against ingest/rows.py:

- `read_rows(path)` opens a CSV and returns dicts keyed by the header row. The code shows this (the DictReader call and its docstring), so I left it out.
- `is_blank(row)` is true when every value is empty or whitespace. The code shows this directly, so I left it out.
- `parse_price(text)` turns "12.50" into 1250 cents, and a comma works as the decimal separator. The function's docstring and code already say this, so I left it out.
- `clean(rows)` drops blank rows and converts each price to cents. The docstring and code show this, so I left it out.
- "The module only uses the standard library's csv module." The only import in rows.py is `import csv`, so the code already shows this, and I left it out.

No claim on the page contradicts the code.

Nothing else refers to docs/ingest.md. README.md and docs/deploy.md do not link to it. I did not change docs/deploy.md, which is a separate page.
