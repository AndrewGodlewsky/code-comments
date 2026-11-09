I fixed two wrong comments in `ledger/export.py`. No code changed.

- **`export_csv` docstring:** it said "newest entry first", but the code sorts by `date` ascending, so the oldest entry comes first. I changed it to "oldest entry first".
- **Comment in `_safe`:** it said "Strip leading and trailing whitespace from the memo", but the function strips nothing. It prefixes a quote when the memo starts with `=`, `+`, `-` or `@`. I replaced it with "Neutralise memos that a spreadsheet would run as a formula."

The other comments are accurate: the module docstring, the formula-prefix note, and the pence-to-pounds note.

One thing I left alone is `# noqa: C901` on `export_csv`. It's a lint suppression, not a comment, and the function is simple enough that it probably isn't needed. Removing it would be a code change, so it's your call.
