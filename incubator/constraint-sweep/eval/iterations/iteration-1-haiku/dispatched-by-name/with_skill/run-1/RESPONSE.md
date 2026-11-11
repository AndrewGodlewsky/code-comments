Removed two dead functions from events/handlers.py:

- `handle_refund_v1`: nothing calls it. The 1.3.0 changelog entry says the refund_v1 kind is no longer accepted, and config/routes.ini does not list it, so events/dispatch.py cannot reach it by name.
- `format_old_receipt`: nothing calls it. The 1.2.0 changelog entry says receipts moved to the billing service.

Kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. `handle_refund` and `handle_chargeback` are reached by name through events/dispatch.py for the kinds switched on in config/routes.ini, and `handle_payout` is imported by payouts/batch.py.

Constraint sweep: config/routes.ini:1-3 says removing a handler breaks every event of its kind. That only applies to kinds listed in the file, and refund_v1 is not one of them, so it did not block the removal. No stale constraints were found in the other files.

Tests: `python -m unittest discover -s tests -t .` passes (5 tests).
