I removed two dead functions from `events/handlers.py`: `handle_refund_v1` and `format_old_receipt`. I did not run the tests.

- `handle_refund_v1`: nothing calls it. `config/routes.ini` no longer lists a `refund_v1` kind, so `events/dispatch.py` cannot reach it. `CHANGELOG.md:7` says the same.
- `format_old_receipt`: nothing calls it. `CHANGELOG.md:10` says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, and `CHARGEBACK_FEE` with them. `handle_refund` and `handle_chargeback` have no direct Python caller, but `events/dispatch.py:23` looks them up as `getattr(handlers, "handle_" + kind)`. `config/routes.ini:2-4` says removing one breaks every event of its kind. `handle_payout` is also imported by `payouts/batch.py`.

I found no stale constraints.
