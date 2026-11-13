I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. Nothing calls it, and `refund_v1` is not in `config/routes.ini`, so dispatch never reaches it. CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt`. Nothing calls it, and CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, and `CHARGEBACK_FEE`. `events/dispatch.py` finds the first three by name from the kinds switched on in `config/routes.ini`, so they have no direct Python caller even though they are live. `handle_payout` is also called directly by `payouts/batch.py`.

The unit tests pass (5 run, all OK). I did not touch the CHANGELOG, which still mentions the removed names as history.

Outside this change, I noticed `events/__init__.py` and `payouts/batch.py` each have two module docstrings, and the second one in each is a stray line. I left both alone because they are outside `events/handlers.py`.
