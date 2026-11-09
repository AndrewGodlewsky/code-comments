I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **The `export_csv` docstring said "newest entry first".** The code sorts with `sorted(entries, key=lambda e: e["date"])`, which is ascending, so the output is oldest first. The docstring now says "oldest entry first".

2. **The `_safe` comment said "Strip leading and trailing whitespace from the memo."** The function never strips anything. It only prefixes a single quote to memos that start with `=`, `+`, `-` or `@`. The comment now says it quotes a memo that a spreadsheet would read as a formula, so it shows as text.

Checked and left as they are:
- The comment above `FORMULA_PREFIXES` is accurate. It describes the formula risk and the quote-prefix defence.
- The pence-to-pounds comment matches the `/ 100` and `.2f` formatting.
- The module docstring and the copyright and SPDX header are fine. I cannot verify the copyright year from the file alone.

Not changed, because it is code rather than a comment: `def export_csv(entries):  # noqa: C901`. The function is short and simple, so the complexity suppression looks unnecessary. It may be worth removing in a code change.
