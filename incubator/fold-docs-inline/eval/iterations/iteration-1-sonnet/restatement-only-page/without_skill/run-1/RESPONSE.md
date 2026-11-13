I deleted `docs/ingest.md`.

Almost everything on the page already lived in the code. `read_rows`, `parse_price` and `clean` already have docstrings that say the same thing, including the comma decimal separator. The line that the module only uses the standard `csv` module is visible from the imports. I did not copy any of that over.

The one gap was `is_blank`, which had no docstring. I added one to `ingest/rows.py`: "Return True when every value in the row is empty or only whitespace."

Nothing else linked to the page. `README.md` and `docs/deploy.md` don't mention it. I haven't run the tests, since the change only adds a docstring.
