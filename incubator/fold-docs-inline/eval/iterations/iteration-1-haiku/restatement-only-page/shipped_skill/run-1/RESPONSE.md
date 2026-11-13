I retired docs/ingest.md and moved its content into the code. The three tests still pass.

What I did:

- `read_rows`, `parse_price` and `clean` already had docstrings that cover what the page said about them, so I left them unchanged.
- `is_blank` had no docstring. I added one stating that it returns True when every value in the row is empty or only whitespace.
- The page's note that the module only uses the standard library's `csv` module is a constraint for future editors, so I added it to the module docstring in `ingest/rows.py`.
- I deleted `docs/ingest.md`. Nothing in the repository links to it.

I left `docs/deploy.md` and `README.md` as they were. The deploy schedule (etl-2, Mondays at 07:00, uploads by 06:00) describes the deployment, not the ingest code, so it stays in the deploy page.
