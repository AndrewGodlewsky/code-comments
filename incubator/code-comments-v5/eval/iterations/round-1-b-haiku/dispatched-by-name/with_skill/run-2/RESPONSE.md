I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. CHANGELOG 1.3.0 replaced it with `handle_refund`, and the `refund_v1` kind is no longer accepted. `config/routes.ini` does not switch it on, so `events/dispatch.py` rejects it with a KeyError before it could look the handler up.
- `format_old_receipt`. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here. Nothing in the repository calls it.

I kept these, because each has a live caller:

- `handle_refund`: used by `tests/test_handlers.py` and reached through dispatch.
- `handle_chargeback` and `CHARGEBACK_FEE`: `config/routes.ini` lists `chargeback = on`, and dispatch finds the handler by name at runtime. `events/handlers.py` has no direct Python caller for it, and the routes file's comment says so.
- `handle_payout`: used by `payouts/batch.py`.

I did not change any comments. The module docstring, the `CHARGEBACK_FEE` comment and the routes file comment all still describe the code that remains. The CHANGELOG entries that mention the removed functions are release history, so I left them alone.

Tests: `python -I -m unittest discover -s tests -t .` ran 5 tests, all passing.

Nothing was committed. This directory is not one I committed from, and the eval instructions ruled out git.
