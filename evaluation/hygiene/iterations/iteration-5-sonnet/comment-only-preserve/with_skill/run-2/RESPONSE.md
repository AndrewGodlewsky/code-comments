I reviewed the comments in `ledger/export.py` and fixed two that were wrong. I changed no code.

1. The `export_csv` docstring said "newest entry first". The code sorts by date ascending, so the oldest entry comes first. I changed the docstring to "oldest entry first".
2. In `_safe`, the comment "Strip leading and trailing whitespace from the memo" was false, because the function never strips anything. I deleted it. The module-level comment above `FORMULA_PREFIXES` already explains the quote prefix, so a replacement would only repeat it.

I left these alone because they are accurate: the license header, the `# noqa: C901` directive, the formula-prefix comment, and the pence-to-pounds comment.

If the docstring's "newest first" was the intended order, the sort is what needs changing, not the comment. I haven't touched the sort, since you asked for no code changes.
