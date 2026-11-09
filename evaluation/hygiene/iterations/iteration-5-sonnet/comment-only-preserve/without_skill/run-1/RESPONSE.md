I reviewed the comments in `ledger/export.py` and fixed two that were wrong. I changed no code.

1. The `export_csv` docstring said "newest entry first". The code sorts by `date` ascending, so the output is oldest first. The docstring now says "oldest entry first".
2. The comment in `_safe` said "Strip leading and trailing whitespace from the memo." The function doesn't strip anything. It prefixes a quote to memos that start with `=`, `+`, `-` or `@`. The comment now says "Defuse memos that a spreadsheet would run as a formula."

I left these alone because they are accurate:
- The module docstring.
- The `FORMULA_PREFIXES` comment.
- The pence-to-pounds comment.
- The license header.

I also left the `# noqa: C901` on `export_csv`. It is a linter directive rather than prose, and the function looks too simple to need it. You may want to check whether it is still necessary, but that would mean changing the code line, so I didn't touch it.
