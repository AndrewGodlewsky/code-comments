I reviewed the comments in `ledger/export.py` against the code and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring**: it said "newest entry first", but the code sorts by `date` ascending, so the output is oldest first. It now reads "oldest entry first".
2. **Comment above `_safe`**: it said the function strips leading and trailing whitespace from the memo. It does not; it only prefixes a single quote when the memo starts with one of `FORMULA_PREFIXES`. The comment now says it guards memos that spreadsheets would run as formulas, and points to `FORMULA_PREFIXES` for the reason, which is already explained there.

Checked and left as written: the license header, the module docstring, the `FORMULA_PREFIXES` comment (the list matches it), the pence-to-pounds comment (the code divides by 100), and the `# noqa: C901` directive.

Not changed: the `_safe` comment now defers to the `FORMULA_PREFIXES` comment rather than restating it. If you would rather the stripping behaviour be added as a feature, that is a code change and outside this request.

Note: the request asked me to read the SKILL.md at `C:\Users\godle\orca\workspaces\code-comments\threadfin\plugins\code-comments\skills\code-comments\SKILL.md`, which is outside the exercise directory. I read that one file for instructions only and changed nothing there.
