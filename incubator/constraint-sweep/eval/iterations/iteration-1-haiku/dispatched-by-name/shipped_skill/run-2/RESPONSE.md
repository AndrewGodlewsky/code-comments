I removed two dead functions from events/handlers.py:

- `handle_refund_v1`. Its kind is not switched on in config/routes.ini, and the 1.3.0 changelog entry says the refund_v1 kind is no longer accepted, so nothing can reach it.
- `format_old_receipt`. Nothing calls it, and the 1.2.0 changelog entry says it is no longer used here.

I kept the other handlers and CHARGEBACK_FEE. `handle_refund`, `handle_chargeback` and `handle_payout` have no direct Python caller, but `events/dispatch.py` reaches each one by name for the kinds switched on in config/routes.ini, and `payouts/batch.py` calls `handle_payout` directly.

I left CHANGELOG.md alone, since it is accurate release history. The module docstring and the other comments in the file are still true after the removal. The unit tests pass (5 of 5). I did not commit anything.
