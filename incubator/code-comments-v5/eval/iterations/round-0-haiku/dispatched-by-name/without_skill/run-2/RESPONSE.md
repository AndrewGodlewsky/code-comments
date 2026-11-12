I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. The `refund_v1` kind was dropped in 1.3.0 (CHANGELOG.md), and `config/routes.ini` no longer lists it, so `events/dispatch.py` can never reach it.
- `format_old_receipt`. Receipts moved to the billing service in 1.2.0 (CHANGELOG.md), and nothing in this repo references it.

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. `dispatch.py` reaches the first three by name from `routes.ini` (`refund`, `chargeback`, `payout`), and `CHARGEBACK_FEE` is used by `handle_chargeback`. `handle_payout` is also called directly by `payouts/batch.py`.

I did not run the test suite, since this exercise asked for edits only. The edit is safe by inspection: the removed names have no references in the repo outside CHANGELOG.md, and `pence` is still used by the remaining handlers, so the import stays.
