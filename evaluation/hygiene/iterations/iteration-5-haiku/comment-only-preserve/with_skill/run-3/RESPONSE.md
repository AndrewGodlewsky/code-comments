I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring said "newest entry first".** The function sorts by `e["date"]` ascending, so the output is oldest first. The docstring now says "oldest entry first".
2. **`_safe` had a comment saying it strips leading and trailing whitespace.** It doesn't; it only prefixes a quote to memos that start with a formula character. The comment was false, and the fact it stated is already covered by the comment above `FORMULA_PREFIXES`, so I deleted it rather than rewording it.

Everything else is accurate and I left it word for word: the copyright and licence header, the module docstring, the formula-injection rationale above `FORMULA_PREFIXES`, the pence-to-pounds comment, and the `# noqa: C901` directive.

Two things for you to check:
- Nothing in the repo explains why the output is sorted by date at all. The docstring now says what the order is, but not why, and I did not invent a reason.
- `ledger/__init__.py` is empty, so there were no other comments to review.
