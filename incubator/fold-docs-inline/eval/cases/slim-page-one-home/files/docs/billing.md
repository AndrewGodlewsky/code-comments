# Billing

`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent.

Totals are rounded half-up, not with Python's default half-even rounding, because the tax
office's e-invoice validator rejects totals rounded half-even (FIN-88).

`invoice_lines()` returns the order's lines sorted by SKU. They are kept in SKU order
because customers check printed invoices against their packing slips, which list items by
SKU.

## Who to ask

Invoice disputes go to the finance team's FINQ queue, not to engineering. Questions about
the e-invoice format go to the accounts-receivable lead.
