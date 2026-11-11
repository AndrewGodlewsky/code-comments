I removed two dead functions from `events/handlers.py`:

- `_legacy_refund_v1`: replaced by `handle_refund` in 1.3.0 (per the CHANGELOG), with no callers anywhere.
- `format_old_receipt`: receipts moved to the billing service in 1.2.0, with no callers anywhere.

I left `handle_refund`, `handle_chargeback` and `CHARGEBACK_FEE` alone. `handle_chargeback` has no direct Python caller, but `config/routes.ini` names it and `events/dispatch.py` looks handlers up by name at runtime, so removing it would break chargeback events. `handle_payout` is used by `payouts/batch.py`, and `handle_refund` by the tests and routes.

I did not run the tests.
