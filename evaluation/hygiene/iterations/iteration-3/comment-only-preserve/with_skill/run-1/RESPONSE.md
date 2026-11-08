I reviewed the comments in `ledger/export.py` and fixed the two that were wrong. No code was changed.

1. **`export_csv` docstring** said the entries come out "newest entry first". The code sorts by `date` ascending, so the output is oldest first. I changed the docstring to "oldest entry first".
2. **`_safe` comment** said "Strip leading and trailing whitespace from the memo." The function does no stripping, so the comment was false. I deleted it. The reason for the function is already explained by the comment above `FORMULA_PREFIXES`.

Left as they were: the license header, the module docstring, the `# noqa: C901` directive, the formula-prefix comment (it matches the code), and the pence-to-pounds comment (it matches the code).

Nothing is missing a reason that I could verify, so I did not add any rationale. The ascending date sort has no comment, and I did not invent one. If the accounts team needs a particular order, that reason should come from them.
