# Billing

`billing.totals.compute_total` returns an invoice total. It rounds each line to the
cent before adding, so the total matches the printed line amounts.

Apply discounts with `billing.discounts.apply_discount` first.
