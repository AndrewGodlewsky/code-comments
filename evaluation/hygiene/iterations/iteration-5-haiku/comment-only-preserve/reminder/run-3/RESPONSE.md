I reviewed the comments and docstrings in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring** said the CSV is "newest entry first". The code sorts with `sorted(entries, key=lambda e: e["date"])`, which is ascending, so the output is oldest first. The docstring now says "oldest entry first".

2. **Comment in `_safe`** said "Strip leading and trailing whitespace from the memo." The function never strips anything. It only prefixes a single quote when the memo starts with a formula character. I deleted the comment, since the comment above `FORMULA_PREFIXES` already explains why.

Checked and left alone: the module header and license lines, the `FORMULA_PREFIXES` comment (accurate, including the quote prefix), and the pence-to-pounds comment in `export_csv` (accurate).
