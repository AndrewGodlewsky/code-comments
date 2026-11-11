I removed two dead functions from events/handlers.py: `handle_refund_v1` and `format_old_receipt`. Nothing else in that file was dead, so the rest is unchanged.

- `handle_refund_v1` had no callers. The `refund_v1` kind is not in config/routes.ini, so dispatch never reaches it, and CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt` had no callers. CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback`, `handle_payout`, `CHARGEBACK_FEE` and the `pence` import. Each is used either through dispatch (the kinds switched on in config/routes.ini) or by payouts/batch.py.

The test suite passes (5 tests). I did not touch CHANGELOG.md, README.md or config/routes.ini.
