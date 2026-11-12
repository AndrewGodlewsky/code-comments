I removed two functions from `events/handlers.py` that nothing calls any more:

- `handle_refund_v1`: its kind `refund_v1` is not in `config/routes.ini`, and CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt`: no references anywhere in the repository, and CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. `handle_refund`, `handle_chargeback` and `handle_payout` are reached through `events/dispatch.py`, which looks up `handle_<kind>` by name for each kind switched on in `config/routes.ini`, and `payouts/batch.py` calls `handle_payout` directly. `CHARGEBACK_FEE` is used by `handle_chargeback`. The `pence` import is still used.

The unit tests pass (5 tests, `python -m unittest discover -s tests -t .`).
