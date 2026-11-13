I removed two dead functions from `events/handlers.py`. The other three handlers and `CHARGEBACK_FEE` stay.

Removed:
- `handle_refund_v1`. The `refund_v1` kind was retired in 1.3.0 (CHANGELOG.md), and `config/routes.ini` does not switch it on, so `events/dispatch.py` raises `KeyError` before it could reach this function. Nothing in the repo calls it.
- `format_old_receipt`. Receipts moved to the billing service in 1.2.0 (CHANGELOG.md). No caller exists in the repo.

Kept:
- `handle_refund`: used by `tests/test_handlers.py` and dispatched for the `refund` kind.
- `handle_chargeback`: dispatched for the `chargeback` kind in `config/routes.ini`. It has no direct Python caller, so it looks unused from the code alone, but removing it would break chargeback events.
- `handle_payout`: called by `payouts/batch.py`.
- `CHARGEBACK_FEE`: used by `handle_chargeback`.

The module docstring and the `CHARGEBACK_FEE` comment remain accurate, so I left them unchanged. I did not touch CHANGELOG.md, which already records both removals' history.

Verification: `python -m unittest discover -s tests -t .` runs 5 tests and all pass.
