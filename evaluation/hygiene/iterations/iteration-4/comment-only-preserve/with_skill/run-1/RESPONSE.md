I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring** said the entries come back "newest entry first". The function sorts by `date` ascending, so the output is oldest first. The docstring now says "oldest entry first".
2. **Comment in `_safe`** said "Strip leading and trailing whitespace from the memo." The function does not strip anything; it only prefixes a single quote when the memo starts with one of `FORMULA_PREFIXES`. The formula-prefix behaviour is already explained in the comment above `FORMULA_PREFIXES`, so I deleted the false comment rather than repeat the fact.

Left as written: the copyright and SPDX header, the module docstring, the formula-prefix comment (it matches `FORMULA_PREFIXES` and `_safe`), the pence-to-pounds comment (it matches the `/ 100`), and the `# noqa: C901` directive.

One observation outside the comments, not changed: `_safe` checks `memo.startswith(...)` without stripping whitespace, so a memo with a leading space before `=` would not be prefixed. If that matters to the accounts team, it is a code question for you to decide.
