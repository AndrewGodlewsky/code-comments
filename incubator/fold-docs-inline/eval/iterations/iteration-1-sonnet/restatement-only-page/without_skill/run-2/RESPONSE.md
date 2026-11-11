I deleted `docs/ingest.md`. Almost everything on it was already in the code, so only one thing needed moving.

- `read_rows`, `parse_price` and `clean` already had docstrings saying what the page said, so I left them alone.
- `is_blank` had no docstring, and the page was the only place that said what counts as blank. I added one to `ingest/rows.py`: it returns True when every value in the row is empty or only whitespace.
- I dropped the closing line saying the module only uses the standard library's `csv` module. The `import csv` line already shows that, and keeping it in prose would go stale.

Nothing else linked to the page. `README.md` and `docs/deploy.md` don't mention it. I didn't run the tests; the change only adds a docstring.
