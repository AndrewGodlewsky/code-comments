I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`: nothing calls it. `refund_v1` is not in `config/routes.ini`, and CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt`: nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. `handle_refund` and `handle_chargeback` are reached by name through `dispatch` for the kinds switched on in `config/routes.ini`, so they have no direct Python caller and must stay. `handle_payout` is called by `payouts/batch.py`. The `pence` import is still used.

The test suite passes (`python -m unittest discover -s tests -t .`, 5 tests OK). No references to the removed functions remain in the repository.
