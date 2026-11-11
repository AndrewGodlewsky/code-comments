docs/ingest.md is gone. Nothing on it needed moving, because ingest/rows.py already says all of it:

- **`read_rows` returns rows as dicts keyed by the header row.** Dropped: its docstring says so.
- **`is_blank` is true when every value is empty or whitespace.** Dropped: its one-line body reads exactly that way.
- **`parse_price` turns "12.50" into 1250 cents, and accepts a comma.** Dropped: its docstring already gives cents and both "12.50" and "12,50".
- **`clean` removes blank rows and converts prices to cents.** Dropped: its docstring says so.
- **The module only uses `csv` from the standard library.** Dropped: the imports show it.

I added no comments, left the docstrings as they were, and changed no code. docs/deploy.md and README.md are untouched.
