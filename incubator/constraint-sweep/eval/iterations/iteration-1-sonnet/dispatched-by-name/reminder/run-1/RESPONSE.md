I removed `handle_refund_v1` and `format_old_receipt` from `events/handlers.py`. Both were dead, and I confirmed that by grepping every file type in the repo.

- `handle_refund_v1` had no callers. The 1.3.0 changelog entry says `handle_refund` replaced it and the `refund_v1` kind is no longer accepted. `config/routes.ini` does not list `refund_v1` either.
- `format_old_receipt` had no callers. The 1.2.0 changelog entry says receipts moved to the billing service.

I kept `handle_chargeback`. Nothing in Python imports it, but `config/routes.ini` says `events/dispatch.py` finds each handler by name at runtime (`getattr(handlers, "handle_" + kind)`). It is the handler for the enabled `chargeback` kind, so removing it would break every chargeback event. `handle_refund` and `handle_payout` are kept for the same reason, and `handle_payout` is also imported by `payouts/batch.py`. `CHARGEBACK_FEE` is still used.

The tests pass (`python -m unittest discover`). Note that `handle_chargeback` has no test coverage.
