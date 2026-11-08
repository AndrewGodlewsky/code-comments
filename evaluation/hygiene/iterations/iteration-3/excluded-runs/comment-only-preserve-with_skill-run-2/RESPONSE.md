I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. `export_csv` docstring said the CSV is "newest entry first". The code sorts by `date` ascending, so the output is oldest first. The docstring now says "oldest entry first".
2. The `_safe` comment said it strips leading and trailing whitespace from the memo. It does not; it only prefixes a memo that starts with `=`, `+`, `-` or `@` with a single quote. The comment now describes that.

Left as they are, because they are accurate:
- The module docstring and the `FORMULA_PREFIXES` comment.
- The comment on the pence-to-pounds conversion.
- The `# noqa: C901` marker.

One thing I did not change: the header says "Copyright 2025". I cannot tell from the file whether that year is still correct, so I left it for you to decide.

I could not read the `SKILL.md` you pointed to. It is outside the repository directory, and this exercise says not to read anything outside it apart from `ledger/export.py`. I followed the review using the comment conventions visible in the file itself.
