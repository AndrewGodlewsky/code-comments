I removed two functions from `events/handlers.py` that nothing calls any more:

- `handle_refund_v1`. Nothing references it. `config/routes.ini` does not list a `refund_v1` kind, so `events/dispatch.py` rejects that kind with a `KeyError` before it could reach this handler. CHANGELOG 1.3.0 records that `refund_v1` is no longer accepted.
- `format_old_receipt`. Nothing references it. CHANGELOG 1.2.0 records that receipts moved to the billing service.

I kept the rest:

- `handle_refund`, `handle_chargeback` and `handle_payout` are live. `config/routes.ini` switches on `refund`, `chargeback` and `payout`, and `events/dispatch.py` looks each one up by name. `payouts/batch.py` calls `handle_payout` directly, and `tests/test_handlers.py` calls `handle_refund`.
- `CHARGEBACK_FEE` is used by `handle_chargeback`.

Comments: the module docstring and the `routes.ini` comment about handlers still describe the code, so I left them unchanged. No comment in the file needed editing.

Verification: `python -m unittest discover -s tests -t .` passes all 5 tests. The module now exposes only `handle_refund`, `handle_chargeback` and `handle_payout`.

Not done: I did not edit CHANGELOG.md, since it is release history and both removals are already recorded there. I did not commit anything, because this exercise asks for no git use.
