I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. Nothing calls it. `dispatch` only reaches a handler for a kind listed in `config/routes.ini`, and `refund_v1` is not listed. CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt`. Nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept the other three handlers:

- `handle_refund` and `handle_chargeback` look like dead code to a plain grep, but `dispatch` finds them at runtime with `getattr(handlers, "handle_" + kind)` for the `refund` and `chargeback` kinds in `config/routes.ini`. Removing them would break those events.
- `handle_payout` is called directly by `payouts/batch.py`.

The module docstring and the comments in `config/routes.ini` still describe the code accurately after the change. The CHANGELOG entries that mention the removed functions are history, so I left them alone.

The unit tests pass (5 of 5). I did not commit anything, because this exercise excluded git.
