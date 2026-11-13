I removed two dead functions from events/handlers.py: `handle_refund_v1` and `format_old_receipt`.

- `handle_refund_v1`: nothing calls it. `dispatch` only reaches `handle_<kind>` for kinds switched on in config/routes.ini, and `refund_v1` is not listed there. CHANGELOG 1.3.0 records that the kind is no longer accepted.
- `format_old_receipt`: nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

I grepped the whole repository (all file types) for both names. The only remaining references are the two CHANGELOG entries, which I kept as release history.

No comment, docstring, or test required either function's behaviour. The routes.ini warning about `handle_<kind>` lookups applies only to the live kinds (refund, chargeback, payout), and all three handlers are still present and unchanged. `CHARGEBACK_FEE` and `pence` are still used.

Tests: `python -m unittest discover -s tests -t .` passes (5 tests), run before and after the change.
