I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring said "newest entry first".** The function sorts by `date` ascending, so the output is oldest first. The docstring now says "oldest entry first".

2. **`_safe` comment said "Strip leading and trailing whitespace from the memo".** The function does no stripping. It only prefixes a single quote when the memo starts with one of `FORMULA_PREFIXES`, and returns everything else unchanged. The comment now says that.

Comments I checked and left alone because they are accurate: the module-level note on `FORMULA_PREFIXES`, the pence-to-pounds note in the loop, and the copyright/licence header (I cannot verify the licence claim from this file alone).

Two things I noticed but did not act on, since they are code, not comments:
- The `# noqa: C901` on `export_csv` looks unnecessary. The function is a short loop with no branching, so the complexity suppression may be stale and could be removed.
- `_safe` checks `memo.startswith(...)` without stripping, so a memo with leading whitespace such as `" =SUM(A1)"` would not be protected. The comment now describes the current behaviour accurately, so if that gap matters, it needs a code change.

The edited file is `C:\Users\godle\AppData\Local\Temp\claude\e73cf29134d8d605\0fa5d545-442b-4519-843c-625f83dfddf5\scratchpad\hygiene-workspace\iteration-1\comment-only-preserve\without_skill\run-1\outputs\ledger\export.py`.
