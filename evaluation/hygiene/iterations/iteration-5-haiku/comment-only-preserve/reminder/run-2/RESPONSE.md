I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. The `export_csv` docstring said the entries come back "newest entry first". The code sorts by `date` ascending, so the output is oldest first. I changed the docstring to "oldest entry first".
2. The comment in `_safe` said "Strip leading and trailing whitespace from the memo." The function does not strip anything; it only prefixes a quote when the memo starts with a formula character. I deleted the comment. The module-level comment above `FORMULA_PREFIXES` already explains why the quoting happens.

The other comments checked out: the copyright and licence header, the module docstring, the formula-injection explanation above `FORMULA_PREFIXES`, and the pence-to-pounds comment in the loop.

One thing I noticed but did not change, because it is code rather than a comment: `_safe` only checks the first character against `=`, `+`, `-` and `@`. Spreadsheet apps can also treat a leading tab or carriage return as the start of a formula, and those are not covered. The top comment describes the four listed characters, so it is accurate as written.
