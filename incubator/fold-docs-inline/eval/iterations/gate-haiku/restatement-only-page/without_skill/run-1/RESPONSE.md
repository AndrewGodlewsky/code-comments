I retired `docs/ingest.md`. The page had five items, and the code already covered four of them:

- `read_rows(path)`: already documented in its docstring (returns each data row as a dict keyed by the header row).
- `parse_price(text)`: already documented in its docstring ("12.50" and "12,50" become cents).
- `clean(rows)`: already documented in its docstring (drops blank rows and converts prices to cents).
- "The module only uses the standard library's `csv` module": this is visible from the import at the top of `ingest/rows.py`, so I did not copy it anywhere.
- `is_blank(row)`: had no docstring, so I added one to `ingest/rows.py`: "Return True when every value in the row is empty or only whitespace."

Nothing else in the repository linked to `docs/ingest.md`, so deleting it breaks no references. `README.md` and `docs/deploy.md` were left unchanged. The unit tests pass (3 of 3). I did not commit anything, since git was out of scope for this exercise.
