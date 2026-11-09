I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **Sort order in the `export_csv` docstring.** It said "newest entry first", but the code sorts with `sorted(entries, key=lambda e: e["date"])`, which puts the oldest entry first. I changed the docstring to "oldest entry first". If newest-first was actually intended, the bug is in the code, not the comment, and that needs your decision.

2. **Whitespace comment in `_safe`.** It said "Strip leading and trailing whitespace from the memo", but `_safe` does not strip anything. It only prefixes a quote when the memo starts with a formula character. I deleted the comment. The existing comment above `FORMULA_PREFIXES` already states the real behaviour.

Left as written: the copyright and SPDX header, the module docstring, the `FORMULA_PREFIXES` comment, the pence-to-pounds comment, and the `# noqa: C901` directive on `export_csv`.

Nothing else in the file needed a change.
