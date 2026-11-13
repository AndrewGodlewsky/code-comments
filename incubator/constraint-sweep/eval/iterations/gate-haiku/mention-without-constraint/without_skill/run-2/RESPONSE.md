I added an optional `currency` argument to `round_price` in `pricing/rounding.py`:

- `round_price(amount, currency="CHF")` rounds to the nearest 0.05 (halves round up), then returns a two-decimal Decimal.
- `round_price(amount)` with no currency behaves exactly as before: it rounds to the cent with halves rounding up.
- Any other currency code also falls back to cent rounding. If you want other currencies to get their own steps, that is a small follow-up.

I added tests in `tests/test_rounding.py` covering the no-currency path, CHF rounding (including the 2.325 halfway case, which rounds up to 2.35), and a non-CHF currency. All 9 tests pass with `python -m unittest discover -s tests -t .`.

Existing callers (`tax.py`, `lines.py`, `labels.py`, `reports.py`) pass no currency, so their behaviour is unchanged. None of them round CHF amounts yet, so the new path is not wired into any price display or invoice total.
