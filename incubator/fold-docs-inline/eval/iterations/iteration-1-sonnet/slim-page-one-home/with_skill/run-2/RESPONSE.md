I slimmed docs/billing.md rather than deleting it, because the "Who to ask" section has no home in the code. Two claims moved into comments, nothing changed in code or tests, and I did not run the tests.

Fate list, in page order:
1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." Dropped. billing/totals.py `invoice_total` has the sum, the `quantize(CENT)` and a docstring that says the same.
2. "Totals are rounded half-up, not Python's default half-even." Dropped as a bare fact. `ROUND_HALF_UP` and `test_total_rounds_half_up` already state it.
3. "...because the tax office's e-invoice validator rejects half-even totals (FIN-88)." Moved. It is now a comment on the `quantize` call in `invoice_total` in billing/totals.py, with the ticket id kept.
4. "`invoice_lines()` returns the order's lines sorted by SKU." Dropped. The `sorted(..., key=lambda line: line.sku)` call in billing/lines.py and `test_lines_come_back_in_sku_order` state it.
5. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." Moved. It is now a comment above the `sorted` call in `invoice_lines` in billing/lines.py.
6. "Invoice disputes go to the finance team's FINQ queue, not to engineering." Kept. It is about another team, and no code here relies on it.
7. "Questions about the e-invoice format go to the accounts-receivable lead." Kept, for the same reason.

Nothing was not migrated: no claim on the page contradicts the code.

Other places that state a moved fact:
- AGENTS.md line 5 repeats the half-up rule and FIN-88. I left it alone for you to reconcile.

Links to the page: none of the files I was given link to docs/billing.md.

Gaps and what is left: claims 6 and 7 are about outside teams and I cannot check them against this repository. docs/billing.md still exists and holds only the "Who to ask" section under a "# Billing" heading. You could move that section to a team or contacts page and then delete the file.
