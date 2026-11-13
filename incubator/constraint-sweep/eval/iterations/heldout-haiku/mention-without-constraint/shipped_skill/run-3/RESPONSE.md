I added a `currency` argument to `round_price` in `pricing/rounding.py`.

- `round_price(amount, currency="CHF")` rounds to the nearest 0.05 (halves round up), so 2.37 becomes 2.35 and 2.375 becomes 2.40.
- Calling it with no currency, or with any currency other than "CHF", keeps the existing cent rounding exactly as before.
- The `round_price` docstring now mentions the CHF case, since its old "to the cent" wording would otherwise be false for CHF.

I added two tests to `tests/test_rounding.py` covering the no-currency path and the CHF path. All 7 tests pass (`python -m unittest discover -s tests -t .`).

Things to be aware of:
- The existing callers (VAT, invoice lines, labels, daily totals) do not pass a currency, so their behaviour is unchanged. If CHF cash rounding should also apply to shop labels or totals, those call sites need to pass "CHF" explicitly. I did not change them.
- The check is case-sensitive: "chf" falls back to cent rounding.
