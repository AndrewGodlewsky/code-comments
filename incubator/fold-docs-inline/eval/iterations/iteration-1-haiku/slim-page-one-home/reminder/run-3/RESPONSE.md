I retired docs/billing.md. I checked each claim against the code before moving anything.

Moved into code comments:
- billing/totals.py, beside the ROUND_HALF_UP quantize call: round half-up, not half-even, because the tax office's e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py, beside the sorted() call: lines are sorted by SKU because customers check printed invoices against packing slips, which list items by SKU.

Left out because the code already shows it: invoice_total() sums the line amounts and returns a Decimal rounded to the cent; invoice_lines() returns lines sorted by SKU.

Kept in a document because there is no code to sit beside: the "Who to ask" section (invoice disputes go to the finance team's FINQ queue; e-invoice format questions go to the accounts-receivable lead). It now lives in README.md.

Contradictions: none. Nothing on the page conflicts with the code.

Other changes: deleted docs/billing.md, since its content has moved. Code changes are comments only; no behaviour changed. Tests pass (`python -m unittest discover -s tests -t .`, 2 tests OK).

Note: AGENTS.md also states the half-up rule and FIN-88 reason. I left it alone because it is outside the page you asked me to retire. You may want to drop one copy later.
