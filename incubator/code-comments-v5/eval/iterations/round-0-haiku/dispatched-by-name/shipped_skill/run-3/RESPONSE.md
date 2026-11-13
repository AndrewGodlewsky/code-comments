I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. The `refund_v1` kind is no longer accepted (CHANGELOG 1.3.0), and `config/routes.ini` lists only `refund`, `chargeback` and `payout`.
- `format_old_receipt`. Receipts moved to the billing service (CHANGELOG 1.2.0), and nothing in the repo calls it.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`. `events/dispatch.py` reaches them by name (`"handle_" + kind`), and `config/routes.ini` documents that, so they look uncalled to a search but are live. `CHARGEBACK_FEE` is still used by `handle_chargeback`.

Checks: the unit tests in `tests/` pass (5 tests). No references to the two removed names remain in code, config or tests. The CHANGELOG entries that mention them are release history, so I left them alone. No comments in the remaining code became false, so I changed none.
