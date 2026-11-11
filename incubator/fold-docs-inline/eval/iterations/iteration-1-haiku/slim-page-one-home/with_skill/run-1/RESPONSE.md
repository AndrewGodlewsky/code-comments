I folded docs/billing.md into the code. The page is not deleted, because its "Who to ask" section has no code home and stays in the page.

Fate list, in page order:

1. "# Billing" heading: kept, as the title over the kept section.
2. "`invoice_total()` adds up the line amounts": dropped. billing/totals.py `invoice_total` sums `line.amount` from a Decimal start.
3. "returns a `Decimal`": dropped. The `sum(..., Decimal("0"))` and `quantize` calls in `invoice_total` show it.
4. "rounded to the cent": dropped. `CENT = Decimal("0.01")` and the existing docstring state it.
5. "Totals are rounded half-up": dropped as a value. billing/totals.py uses `ROUND_HALF_UP`, and tests/test_billing.py `test_total_rounds_half_up` checks it.
6. "not with Python's default half-even rounding" (the rejected alternative): moved to the `invoice_total` docstring in billing/totals.py.
7. "because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)" (reason): moved to the `invoice_total` docstring in billing/totals.py. Ticket id kept.
8. "`invoice_lines()` returns the order's lines sorted by SKU": dropped. billing/lines.py `invoice_lines` ends with `sorted(..., key=lambda line: line.sku)`, and tests/test_billing.py `test_lines_come_back_in_sku_order` checks it.
9. "They are kept in SKU order because customers check printed invoices against their packing slips": moved to the `invoice_lines` docstring in billing/lines.py (reason, and the constraint a sort change would break).
10. "which list items by SKU": moved with claim 9.
11. "## Who to ask" heading: kept.
12. "Invoice disputes go to the finance team's FINQ queue, not to engineering.": kept. Ownership, with no code home.
13. "Questions about the e-invoice format go to the accounts-receivable lead.": kept. Ownership, with no code home.

No claim was not migrated. The code agrees with every claim on the page.

Edits:
- billing/totals.py: `invoice_total` docstring extended with the half-up rule and FIN-88 reason.
- billing/lines.py: `invoice_lines` docstring extended with the SKU-order reason.
- docs/billing.md: claims 2-10 removed. The page now holds "# Billing", "## Who to ask", and its two kept sentences.
- Nothing else changed. `python -I -m unittest discover -s tests -t .` passes (2 tests).

Other files that state a moved fact, for you to reconcile:
- AGENTS.md line 5 repeats the half-up rule and the FIN-88 reason: "Invoice totals round half-up, never half-even: the e-invoice validator rejects half-even totals (FIN-88)." I did not edit it, because it is an instruction file.

Files that link to docs/billing.md or to the removed sections: none found in this repository.

Gaps you need to fill:
- The e-invoice validator's rejection of half-even totals (claims 6-7) is an outside fact. I cannot check it from this repository. I moved it because the code relies on it. FIN-88 was not checked, because task tracking was out of scope.
- The customers' packing-slip behaviour (claims 9-10) is an outside fact. I cannot check it here. I moved it as the reason for the sort order.
- Decide whether to keep docs/billing.md with its "Who to ask" section, or move that section too. The page is retired only once that section is handled.
