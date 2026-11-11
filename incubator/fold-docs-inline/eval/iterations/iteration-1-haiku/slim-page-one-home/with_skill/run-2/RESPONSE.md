I folded docs/billing.md into the code. The page is not deleted yet, because one section has no code home.

Fate list (page order):

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." - Dropped. billing/totals.py `invoice_total` sums `line.amount` from `Decimal("0")` and quantizes to `CENT`.
2. "Totals are rounded half-up, not with Python's default half-even rounding, because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)." - Moved to the docstring of billing/totals.py `invoice_total`. The code shows `ROUND_HALF_UP`, but not the validator reason or the FIN-88 id.
3. "`invoice_lines()` returns the order's lines sorted by SKU." - Dropped. billing/lines.py `invoice_lines` ends with `sorted(..., key=lambda line: line.sku)`, and tests/test_billing.py `test_lines_come_back_in_sku_order` covers it.
4. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." - Moved to the docstring of billing/lines.py `invoice_lines`. The reason is not in the code.
5. "# Billing" heading - Kept, because the "Who to ask" section sits under it.
6. "## Who to ask" heading - Kept.
7. "Invoice disputes go to the finance team's FINQ queue, not to engineering." - Kept. Operational ownership, with no code here to sit beside.
8. "Questions about the e-invoice format go to the accounts-receivable lead." - Kept. Same reason.

Not migrated: none.

Other files stating a moved fact:
- AGENTS.md line 5 says the same as fact 2 (half-up rounding, FIN-88). Left unchanged, as an instruction file, for you to reconcile.

Files linking to the page or to a removed section: none. A search of AGENTS.md, README.md, docs/setup.md and tests/ found no reference to billing.md.

Gaps for you to decide:
- docs/billing.md is not deleted. It now holds "# Billing" and "## Who to ask" only. Decide where the ownership section should go (a new doc, README.md, or a module docstring), then delete the page.
- The e-invoice validator rule (fact 2) and the packing-slip reason (fact 4) are outside facts. I could not verify them from this repository, so they are recorded as stated on the page.
- The "Who to ask" queue and role names could not be checked against the code, so they are kept as written.

Verification: `python -m unittest discover -s tests -t .` ran with 2 tests passing. Only docs/billing.md, billing/totals.py, billing/lines.py and RESPONSE.md changed.
