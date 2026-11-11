I added an optional `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount)` with no currency is unchanged: it still rounds to the cent, halves up.
- `round_price(amount, "CHF")` rounds to the nearest 0.05, halves up. For example, 2.37 gives 2.35, 2.38 gives 2.40, and 2.375 gives 2.40.
- Any other currency string raises `ValueError`. This is my choice, not something you asked for. The alternative is to fall back to cent rounding, which would hide mistakes. Say if you want a different behaviour.

I added tests for the no-currency default, the CHF cases and the rejection of unknown currencies in `tests/test_rounding.py`. I also updated the `round_price` entry in `README.md`. All 8 tests pass (`python -I -m unittest discover -s tests -t .`).

Constraints I found by grepping the whole repository (code, tests, README, comments and docstrings):

- `pricing/rounding.py`: the module docstring says every amount is rounded there and nowhere else. The CHF path stays in that module, so this still holds.
- `README.md`: calls `round_price` "the one place money is rounded". Still true.
- `invoices/lines.py`: a line is rounded once with `round_price`, not unit by unit (ten items at 0.333 give 3.33). This is unchanged because callers pass no currency.
- `shop/reports.py`: daily totals use `round_price` so they match the invoice lines to the cent. Unchanged for current callers. If daily totals ever need CHF rounding, they would then differ from the cent-based line totals, so that is a decision to make separately.
- `shop/labels.py`: labels pass through `round_price` so a label never shows a fraction of a cent. Unchanged. A CHF label would need a currency passed through `price_label`, which does not exist yet.
- `pricing/tax.py`: VAT is rounded once with `round_price`. Unchanged.

Nothing that existing code returns, orders or accepts has changed. No existing caller passes a currency.
