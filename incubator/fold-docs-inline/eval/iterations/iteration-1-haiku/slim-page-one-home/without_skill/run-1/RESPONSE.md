I moved the code-level rules from docs/billing.md into the code they describe:

- billing/totals.py: the `invoice_total()` docstring now says totals round half-up, not half-even, and gives the reason (the tax office's e-invoice validator rejects half-even totals, FIN-88).
- billing/lines.py: the `invoice_lines()` docstring now says lines are sorted by SKU and why (customers check printed invoices against packing slips, which list items by SKU).

I did not change any behaviour or tests. `python -m unittest discover -s tests -t .` passes (2 tests).

Not moved: the "Who to ask" section of docs/billing.md. Invoice disputes go to the finance team's FINQ queue, and e-invoice format questions go to the accounts-receivable lead. That is contact routing rather than code behaviour, and it would go stale in a code comment. It needs a new home, such as the README or the team's contacts page, before docs/billing.md is deleted.

I left docs/billing.md in place so nothing is lost before that section is relocated. docs/setup.md and README.md are unchanged.
