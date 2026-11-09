I fixed two wrong comments in `ledger/export.py` and changed no code.

- **`export_csv` docstring:** it said "newest entry first", but the code sorts by `date` ascending, so the oldest entry comes first. It now says "oldest entry first".
- **`_safe` comment:** it said "Strip leading and trailing whitespace from the memo", but the function never strips anything. It prefixes a quote when the memo starts with `=`, `+`, `-` or `@`. The comment now says it neutralises memos that a spreadsheet would run as a formula.

I left the other comments alone because they are accurate: the file header, the `FORMULA_PREFIXES` note, and the pence-to-pounds note. I also left `# noqa: C901` in place, since it is a linter directive and not a comment about behaviour.
