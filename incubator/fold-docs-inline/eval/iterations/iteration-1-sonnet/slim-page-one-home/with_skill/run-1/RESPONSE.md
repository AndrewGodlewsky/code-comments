I moved the two reasons from docs/billing.md into comments in the code. I could not retire the page, because the "Who to ask" section has nowhere in the code to sit beside, so the page stays with only that section.

Fate of each claim, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." Dropped. The code and docstring in billing/totals.py `invoice_total` already say this.
2. "Totals are rounded half-up, not Python's default half-even." Moved. billing/totals.py `invoice_total` now has a comment above the `quantize` call. The code and `test_total_rounds_half_up` already show the half-up mode, so the comment adds only the reason.
3. "...because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)." Moved to the same comment in billing/totals.py `invoice_total`. I kept the ticket id.
4. "`invoice_lines()` returns the order's lines sorted by SKU." Dropped. billing/lines.py `invoice_lines` sorts by `line.sku`, and `test_lines_come_back_in_sku_order` covers it.
5. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." Moved. billing/lines.py `invoice_lines` now has a comment above the `sorted` call. I could not check the packing-slip fact against any code here, but it is an outside reason the code relies on, so I moved it as written.
6. "Invoice disputes go to the finance team's FINQ queue, not to engineering." Kept. It is a fact about other systems, with no code here to sit beside.
7. "Questions about the e-invoice format go to the accounts-receivable lead." Kept, for the same reason.

I found no claim the code contradicts.

Other files that state a moved fact:
- AGENTS.md line 5 repeats the half-up rule and FIN-88. I did not touch it. You may want to reconcile it with the new comment.

Files that link to the page:
- None. README.md and docs/setup.md do not link to docs/billing.md.

Gaps:
- None. The "Who to ask" section is not an overview of the module, so it has no natural docstring home. docs/billing.md still holds it under the "Who to ask" heading. The "# Billing" title is still there.

I changed nothing else: no code, tests, AGENTS.md or other docs.
