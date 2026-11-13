I deleted `docs/ingest.md`.

Almost everything on the page was already in the code. `read_rows`, `parse_price` and `clean` already have docstrings that say the same thing, including the comma-as-decimal-separator behaviour. The tests also cover it.

The one gap was `is_blank`, which had no docstring. I added a one-line docstring to it in `ingest/rows.py`.

I did not carry over the line "the module only uses the standard library's `csv` module". The `import csv` at the top of the file already shows that. It would also go stale the first time someone adds an import.

Nothing else in the repo linked to the page. I did not run the tests.
