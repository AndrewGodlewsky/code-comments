I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. The CHANGELOG (1.3.0) says the `refund_v1` kind is no longer accepted, and `config/routes.ini` does not list it. `events/dispatch.py` raises `KeyError` for any kind that is not switched on, so this handler can never run.
- `format_old_receipt`. The CHANGELOG (1.2.0) says receipts moved to the billing service. Nothing in the repository calls it.

I kept the rest:

- `handle_refund`, `handle_chargeback` and `handle_payout` stay. `handle_refund` and `handle_chargeback` are reached through `getattr` in `events/dispatch.py`, using the kinds switched on in `config/routes.ini`. `handle_payout` is called by `payouts/batch.py`. `handle_refund` is also used in `tests/test_handlers.py`.
- `CHARGEBACK_FEE` stays, because `handle_chargeback` uses it.

Checks: the unit tests pass (5 run, OK). The three routed kinds still resolve to their handlers.

I did not touch the CHANGELOG, which still mentions both removed functions as history.
