I added an optional `currency` argument to `round_price` in `pricing/rounding.py`. With `currency="CHF"` it rounds to the nearest 0.05, and halves round up, which matches the existing half-up rule. With no currency, or any currency other than "CHF", the code path is the same as before. I added two tests, one for CHF rounding and one for the unchanged default.

I grepped the whole repository for `round_price` and for rounding and cent wording. The callers are `invoices/lines.py`, `pricing/tax.py`, `shop/labels.py` and `shop/reports.py`. None of them passes a currency, so their results are unchanged. The constraints stated in comments, docstrings and the README are all still met:
- **"The one place money is rounded":** the CHF rule lives inside `round_price`, so this holds.
- **Labels never show a fraction of a cent:** CHF results still have two decimals, so this holds.
- **Report totals match the sum of the invoice lines to the cent (`shop/reports.py`):** this holds today because both use the same rounding. I did not wire CHF into any caller. If you later pass "CHF" in some places but not others, for example in invoice lines but not in report totals, the totals will stop matching the lines. Pass the currency consistently in both places.
- **Invoice lines and VAT round once, on the product or the gross:** unchanged.

I left the callers alone because you only asked for the argument. Let me know if you want CHF threaded through the invoice, tax, label and report code.
