I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

**Changes**

1. `export_csv` docstring said "newest entry first". The code sorts by `date` ascending, so the output is oldest first. I changed the docstring to "oldest entry first" to match the code.
2. The comment in `_safe` said "Strip leading and trailing whitespace from the memo". The function does not strip anything; it only prefixes a quote to memos that start with a formula character. That fact is already stated in the module-level comment above `FORMULA_PREFIXES`, so I deleted the false comment rather than move it.

**Left alone**

- The module-level formula-prefix comment, the pence-to-pounds comment, the copyright header and the `# noqa: C901` directive are accurate and unchanged.

**Questions for you**

- The docstring change assumes oldest-first is intended. If newest-first was the intent, the sort in `export_csv` is the bug, and the docstring should stay as it was. I found no ticket or test that settles it. Which is it?
- The `_safe` comment suggests that stripping whitespace may once have been intended. If so, memos with leading whitespace before a `=`, `+`, `-` or `@` currently skip the quote prefix. That is a code question, so I did not act on it. Should `_safe` strip whitespace first?
- I found no recorded reason for sorting by date at all. If the team needs a specific order, a short reason beside the sort would help the next editor.
