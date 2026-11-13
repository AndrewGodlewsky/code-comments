I retired docs/billing.md and moved the parts that describe code behaviour into docstrings beside that code. The test suite passes (2 tests, `python -m unittest discover -s tests -t .`).

Changes:

- `billing/totals.py`, `invoice_total()`: the docstring now says totals round half-up, not Python's default half-even, because the e-invoice validator rejects half-even totals (FIN-88).
- `billing/lines.py`, `invoice_lines()`: the docstring now says lines are sorted by SKU on purpose, because customers check printed invoices against packing slips that list items by SKU.
- `docs/billing.md`: deleted. No other file in the repo referenced it.
- `docs/setup.md`, `README.md`, `AGENTS.md`: unchanged.

Not moved: the "Who to ask" section. It routes invoice disputes to the finance team's FINQ queue and e-invoice format questions to the accounts-receivable lead. That describes people and process, not code, so it does not belong in code comments. Deleting the file would lose it, so it needs a new home, such as the README or a team page. Its text is below so it is not lost:

> Invoice disputes go to the finance team's FINQ queue, not to engineering. Questions about the e-invoice format go to the accounts-receivable lead.

Decision for you: where that contact text should live.
