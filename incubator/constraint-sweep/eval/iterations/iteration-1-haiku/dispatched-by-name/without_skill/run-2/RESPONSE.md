I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. The refund_v1 kind was dropped in 1.3.0 (CHANGELOG.md), and `config/routes.ini` does not list it, so `events/dispatch.py` can never reach it.
- `format_old_receipt`. Receipts moved to the billing service in 1.2.0 (CHANGELOG.md), and nothing in this repo calls it.

I kept the other handlers. `handle_refund`, `handle_chargeback` and `handle_payout` are live. The dispatcher reaches the first two by name through `routes.ini`, and `payouts/batch.py` calls `handle_payout` directly. `CHARGEBACK_FEE` is used by `handle_chargeback`.

I checked the whole repository for references to the removed names and found only the CHANGELOG mentions. The existing tests do not touch them, so I did not run the suite (no git and no test runner in this exercise). Nothing else changed.
