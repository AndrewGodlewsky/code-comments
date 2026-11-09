I reviewed the comments in `ledger/export.py` and fixed two that were false. I changed no code.

- The `export_csv` docstring said "newest entry first", but the rows are sorted by `date` in ascending order. It now says "oldest entry first".
- The comment in `_safe` said it strips leading and trailing whitespace, but the function does no stripping. It only prefixes memos that start with `=`, `+`, `-` or `@` with a quote. The comment now says that.

I left the rest as written: the license header, the `# noqa: C901` directive, the formula-prefix comment and the pence-to-pounds comment. Each matches the code.

Separately, the code sorts oldest first. If the accounts team wants newest first, the sort is what needs changing. I left it alone because you asked for comment fixes only.
