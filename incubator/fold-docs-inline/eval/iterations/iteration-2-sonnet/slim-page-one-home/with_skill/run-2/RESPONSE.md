I folded docs/billing.md into the code. I did not delete it, because the "Who to ask" section has nowhere in the code to go and stays.

Fate list, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." Dropped. `billing/totals.py` `invoice_total` already says this in its docstring and code (sum, `quantize(CENT)`).
2. "Totals are rounded half-up, not with Python's default half-even rounding." Dropped. `ROUND_HALF_UP` in `invoice_total` and `test_total_rounds_half_up` state it.
3. "...because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)." Moved. A comment above the `quantize` call in `billing/totals.py` `invoice_total` now gives the reason and the FIN-88 id.
4. "`invoice_lines()` returns the order's lines sorted by SKU." Dropped. `sorted(..., key=line.sku)` in `billing/lines.py` `invoice_lines` and `test_lines_come_back_in_sku_order` state it.
5. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." Moved. A comment above the `sorted` call in `billing/lines.py` `invoice_lines` now gives the reason.
6. "Invoice disputes go to the finance team's FINQ queue, not to engineering." Kept. Operational contact, nothing in the code to sit beside.
7. "Questions about the e-invoice format go to the accounts-receivable lead." Kept. Same reason.

Not migrated: nothing. The code contradicts no claim.

Other files stating a moved fact: AGENTS.md line 5 repeats the half-up rule and the FIN-88 reason. Reconcile it if you want one home.
Files linking to docs/billing.md: none found (README.md, AGENTS.md and docs/setup.md have no link).
Gaps: none. docs/billing.md now holds only the "# Billing" title and the "Who to ask" section.
