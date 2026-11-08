I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring** said the entries come out "newest entry first". The code sorts by `e["date"]` ascending, so the output is oldest first. The docstring now says "oldest entry first".

2. **Comment in `_safe`** said "Strip leading and trailing whitespace from the memo". The function does no stripping. It only prefixes a single quote when the memo starts with `=`, `+`, `-` or `@`. The comment now describes that.

The other comments are accurate and I left them alone: the module docstring, the formula-injection explanation above `FORMULA_PREFIXES`, and the pence-to-pounds note in the loop.

Two things I noticed but did not touch, because they are code rather than comments:
- `# noqa: C901` on `export_csv` suppresses a complexity warning the function probably does not trigger. It may be stale.
- The header says `Copyright 2025`. That may be correct, but if the file has been changed since, the year or range might need updating.
