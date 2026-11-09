I reviewed the comments and docstrings in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring**: it said "newest entry first", but the code sorts with `sorted(entries, key=lambda e: e["date"])`, which is ascending, so the output is oldest first. I changed it to "oldest entry first".
2. **Comment in `_safe`**: it said "Strip leading and trailing whitespace from the memo", but the function never strips anything. It only prefixes a quote when the memo starts with a formula character. I deleted the comment, since the module-level comment above `FORMULA_PREFIXES` already explains the behaviour.

Left as they are:
- The module docstring, the copyright/licence header, the `FORMULA_PREFIXES` comment and the pence-to-pounds comment are accurate.
- `# noqa: C901` on `export_csv` is a lint suppression rather than a comment about the code. The function is simple, so the suppression may no longer be needed. I did not remove it because that would be a code change and I could not check the lint configuration.
