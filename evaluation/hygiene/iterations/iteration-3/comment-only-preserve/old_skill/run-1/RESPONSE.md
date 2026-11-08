I reviewed the comments in `ledger/export.py` against the code and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring said "newest entry first".** The code sorts with `sorted(entries, key=lambda e: e["date"])`, which is ascending, so the output is oldest first. I changed the docstring to "oldest entry first". Please confirm which order the accounts team expects. If newest-first is the intent, the sort needs to be reversed, and that is a code change I did not make.

2. **`_safe` had a comment saying it strips leading and trailing whitespace from the memo.** The function does not do that. I deleted the comment. The module-level comment above `FORMULA_PREFIXES` already explains why memos are prefixed, so the removed text was only a false restatement.

Left alone:
- The module header, the `FORMULA_PREFIXES` comment, and the pence-to-pounds comment are accurate.
- The `# noqa: C901` directive and the copyright and licence header are kept.

Two things for you to decide, which I did not act on:
- If whitespace stripping was intended, the code is missing it. I cannot tell from the file whether that was ever planned.
- `_safe` checks `memo.startswith(FORMULA_PREFIXES)` without stripping first, so a memo with leading spaces before `=` would not be quoted. This is a possible behaviour gap, not a comment problem.
