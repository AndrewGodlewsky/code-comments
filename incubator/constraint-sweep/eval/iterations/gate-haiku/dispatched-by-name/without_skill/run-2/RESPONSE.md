I removed two dead functions from `events/handlers.py`:

- `_legacy_refund_v1`: nothing calls it. CHANGELOG 1.3.0 says `handle_refund` replaced it.
- `format_old_receipt`: nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, and `CHARGEBACK_FEE`. `config/routes.ini` names the three handlers and `events/dispatch.py` looks them up by name at runtime, so they have no direct Python callers but are live. `CHARGEBACK_FEE` is used by `handle_chargeback`.

The test suite passes (4 tests, run with `python -m unittest discover -s tests -t .`), and the file parses.
