I moved the two facts from docs/billing.md that describe how the code behaves into the docstrings of the functions they cover:

- `billing/totals.py`, `invoice_total()`: the half-up rounding rule and the FIN-88 reason (the e-invoice validator rejects half-even totals).
- `billing/lines.py`, `invoice_lines()`: the SKU sort order and why it is kept (customers check printed invoices against packing slips, which list items by SKU).

I did not move the "Who to ask" section. It names team routing (FINQ queue for invoice disputes, the accounts-receivable lead for e-invoice format questions), not code behaviour, so it does not belong beside the code. It needs a new home before docs/billing.md is deleted, for example a short ownership note in README.md. I left docs/billing.md in place so that section is not lost; delete it once that is done.

The unit tests pass (`python -m unittest discover -s tests -t .`, 2 tests OK).
