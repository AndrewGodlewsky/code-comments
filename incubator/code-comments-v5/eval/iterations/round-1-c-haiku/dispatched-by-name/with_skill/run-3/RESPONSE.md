I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. Nothing imports it. Dispatch only reaches it for the kind `refund_v1`, which is not switched on in `config/routes.ini`, and CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt`. Nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept the rest:

- `handle_refund`, `handle_chargeback` and `handle_payout` stay. Dispatch looks them up by name for the kinds switched on in `config/routes.ini`, and `handle_refund` and `handle_payout` also have direct callers (the refund test and `payouts/batch.py`).
- `CHARGEBACK_FEE` stays. `handle_chargeback` uses it.

The unit tests pass (5 of 5), and a dispatch smoke test for `refund` returns the expected postings. I did not make any git commit.
