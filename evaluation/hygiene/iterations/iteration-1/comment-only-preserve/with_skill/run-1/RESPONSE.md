I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

**Fixed**

1. The `export_csv` docstring said "newest entry first". The code sorts by `e["date"]` ascending, so the output is oldest first. The docstring now says "oldest entry first".
2. The comment above `_safe` said "Strip leading and trailing whitespace from the memo." The function does not strip anything. It only prefixes a quote when the memo starts with one of `FORMULA_PREFIXES`. The comment now reads "Quote a memo that a spreadsheet would run as a formula; see FORMULA_PREFIXES." That points to the existing explanation at the top of the file rather than repeating it.

**Left as they were**

- The licence header, the module docstring, the formula-injection comment above `FORMULA_PREFIXES`, the pence-to-pounds comment, and the `# noqa: C901` directive. All are accurate.

**For you to decide (not changed)**

- Whether `_safe` was meant to strip whitespace, as the old comment described. If so, the code is missing that step. A memo with leading spaces before `=`, `+`, `-` or `@` currently bypasses the quote. I have not verified how the spreadsheet apps treat leading spaces, so I have not treated this as a confirmed bug.
