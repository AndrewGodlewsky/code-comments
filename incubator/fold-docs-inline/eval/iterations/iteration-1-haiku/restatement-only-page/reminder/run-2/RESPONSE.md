# Retired docs/ingest.md

I deleted docs/ingest.md. I changed no code and created no new files other than this note.

Nothing needed to move. I checked each claim on the page against the code:

- `read_rows(path)` returns rows as dicts keyed by the header row. The code in `ingest/rows.py` does this, and so does its docstring. Left out.
- `is_blank(row)` is true when every value is empty or whitespace. The code does this. `is_blank` has no docstring, but the code already shows the behaviour, so I did not add one. Left out.
- `parse_price(text)` turns "12.50" and "12,50" into 1250 cents. The code does this, and so does its docstring. Left out.
- `clean(rows)` drops blank rows and converts each price to cents. The code does this, and so does its docstring. Left out.
- The module only uses the standard library's `csv` module. `ingest/rows.py` imports only `csv`, and `ingest/__init__.py` is empty. Left out.

The code contradicted none of the claims, so there is nothing to flag. No comments were added, because each fact is already shown by the code or its docstring and a comment would only repeat it. No content had no code to sit beside, so no document was kept.

`README.md` and `docs/deploy.md`, the other docs I read, do not link to `docs/ingest.md`, so deleting it breaks no link I found.
