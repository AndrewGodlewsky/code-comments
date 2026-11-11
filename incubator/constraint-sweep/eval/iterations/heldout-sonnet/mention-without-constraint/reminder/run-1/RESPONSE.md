I added an optional `currency` argument to `round_price` in `pricing/rounding.py`. With "CHF" it rounds to the nearest 0.05. With no currency (the default) the code path is the same as before: round to the cent, halves up.

I grepped every file type for `round_price`. The callers are `invoices/lines.py`, `pricing/tax.py`, `shop/labels.py` and `shop/reports.py`, plus the README and `tests/test_rounding.py`. All of them call it with one argument, so none of them changes.

Constraints stated in those files, and how I handled them:
- The `rounding.py` docstring says every amount is rounded there and nowhere else, and the README says it is the one place money is rounded. I put the CHF rule inside `round_price` rather than adding a second rounding function.
- The docstring and tests say halves round up. CHF also rounds halves up, so 2.375 becomes 2.40.
- `shop/labels.py` says a label never shows a fraction of a cent. The default path still guarantees that, and CHF results keep two decimals.
- The comments in `invoices/lines.py`, `pricing/tax.py` and `shop/reports.py` say each total is rounded once, so that totals match the sum of the invoice lines to the cent. Nothing changes for them. They don't pass a currency, so a CHF invoice would not get 0.05 rounding until they do. If you want that, pass the currency from those callers. All of them round once at the end, so the totals would still agree with each other.

I added tests for the default, CHF rounding and CHF halves. The suite passes.
