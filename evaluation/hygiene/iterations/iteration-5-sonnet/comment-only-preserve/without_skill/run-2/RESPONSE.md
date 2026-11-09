I found two wrong comments in `ledger/export.py` and fixed both. No code was changed.

1. The `export_csv` docstring said "newest entry first". The code sorts by date ascending, so the oldest entry comes first. It now says "oldest entry first".
2. The comment in `_safe` said "Strip leading and trailing whitespace from the memo". The function doesn't strip anything. It prefixes a quote when the memo starts with `=`, `+`, `-` or `@`. The comment now says "Prefix a quote if the memo starts with a formula character."

The other comments are accurate and I left them alone: the license header, the note on `FORMULA_PREFIXES`, and the pence-to-pounds note. I also kept `# noqa: C901`, since it is a lint directive and not prose.

If newest-first was the intended order, the code would need `reverse=True`. I didn't make that change because you asked for comments only.
