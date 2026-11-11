`round_price(amount, currency=None)` now takes a currency argument. With `"CHF"` it rounds to the nearest 0.05, with halves rounding up, so 2.37 gives 2.35 and 2.375 gives 2.40. With no currency it runs the same code path as before, rounding to the cent. I added two tests to `tests/test_rounding.py` and the full suite passes.

I searched the repo for other mentions of `round_price`. The callers are `invoices/lines.py`, `pricing/tax.py`, `shop/labels.py` and `shop/reports.py`. None of them passes a currency, so their behaviour is unchanged. Their comments say things like "rounded once with round_price" and "match the sum of the invoice lines to the cent". Those still hold, because they only describe the default cent rounding. I edited no other file.

Nothing calls it with `"CHF"` yet. If you want Swiss prices in the invoice, tax, label or report code to use it, each caller has to pass the currency. The "to the cent" comments would need rewording at that point.
