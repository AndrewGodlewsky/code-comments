I removed two functions from `events/handlers.py` that nothing calls any more:

- `_legacy_refund_v1`: superseded by `handle_refund` in 1.3.0 (see CHANGELOG.md).
- `format_old_receipt`: receipts moved to the billing service in 1.2.0 (see CHANGELOG.md).

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. The first three are named in `config/routes.ini` and looked up at runtime by `events/dispatch.py`, even though nothing calls them directly in Python. `handle_payout` is also imported by `payouts/batch.py`. `CHARGEBACK_FEE` is used by `handle_chargeback`.

The test suite passes (4 tests, OK). I did not touch CHANGELOG.md, which still describes both removals as history.
