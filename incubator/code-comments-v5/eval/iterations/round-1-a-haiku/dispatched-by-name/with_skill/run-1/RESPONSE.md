I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. The `refund_v1` kind is no longer accepted (CHANGELOG 1.3.0), and it is not in `config/routes.ini`, so `dispatch` raises `KeyError` before it could be looked up.
- `format_old_receipt`. Receipts moved to the billing service (CHANGELOG 1.2.0), and nothing in the repo references it.

I kept these because something still reaches them:

- `handle_refund`: called directly by `tests/test_handlers.py` and routed by `events/dispatch.py`.
- `handle_chargeback` and `handle_payout`: no Python caller. They are looked up by name through `getattr` in `events/dispatch.py` for the kinds `chargeback` and `payout`, which are switched on in `config/routes.ini`. `handle_payout` is also called by `payouts/batch.py`.
- `CHARGEBACK_FEE`: used by `handle_chargeback`.

No comment was made false by the removal. The `config/routes.ini` note about handlers with no direct Python caller still holds for the handlers that remain. I did not touch CHANGELOG.md, since it already records both removals. I did not add a new entry.

Tests: `python -m unittest discover -s tests -t .` runs 5 tests, all passing.
