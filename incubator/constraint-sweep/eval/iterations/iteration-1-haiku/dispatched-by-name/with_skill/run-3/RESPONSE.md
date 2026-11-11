I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`: its kind `refund_v1` is not switched on in `config/routes.ini`, so `dispatch` never reaches it. `CHANGELOG.md` (1.3.0) says the kind is no longer accepted.
- `format_old_receipt`: nothing calls it. `CHANGELOG.md` says receipts moved to the billing service.

`handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE` stay. They are live: `dispatch` looks up `handle_refund`, `handle_chargeback` and `handle_payout` by name for the kinds switched on in `config/routes.ini`, and `payouts/batch.py` imports `handle_payout`.

Constraint sweep:
- `config/routes.ini:2-4` says handlers for listed kinds must not be removed or renamed. I did not touch any listed handler, so it still holds.
- The comment inside `handle_refund_v1` ("Refunds before 1.3 were booked against cash only") went with the function. It was historical and nothing depended on it.
- `CHANGELOG.md` lines 7 and 10 still name the removed functions. They are release history, so I left them alone.

The unit tests pass (5 tests, OK).
