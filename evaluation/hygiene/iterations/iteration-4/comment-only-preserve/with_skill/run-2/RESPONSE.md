I reviewed the comments in `ledger/export.py` against the code and fixed the two that were wrong. No code changed, only comment text.

1. `export_csv` docstring said the entries come back "newest entry first". The code sorts by `date` ascending, so the output is oldest first. I changed the docstring to "oldest entry first".
2. `_safe` had a comment saying it strips leading and trailing whitespace from the memo. It does not. I deleted the comment. The formula-prefix rule it sits under is already documented at `FORMULA_PREFIXES`.

Left as written: the module header, the formula-prefix comment above `FORMULA_PREFIXES`, the pence-to-pounds comment, and the `# noqa: C901` directive.

Two things for you to decide. I did not change code for either:
- If the accounts team actually wants newest first, the sort in `export_csv` needs `reverse=True` and the docstring would then be right as it was. I need to know which is intended.
- `_safe` checks `memo.startswith(...)` with no whitespace handling. A memo with a leading space before `=`, `+`, `-` or `@` would skip the guard. I have not verified whether spreadsheet apps treat that as a formula, so this may be harmless. Worth checking.
