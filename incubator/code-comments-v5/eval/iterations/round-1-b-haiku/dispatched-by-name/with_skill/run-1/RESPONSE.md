I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. Nothing calls it, and `refund_v1` is no longer an accepted kind. `config/routes.ini` does not list it, and CHANGELOG 1.3.0 says it was replaced by `handle_refund`.
- `format_old_receipt`. Nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, and `CHARGEBACK_FEE`. `dispatch.py` looks the first three up by name from `config/routes.ini`, so they have no direct Python caller even though they are live. `handle_payout` is also called by `payouts/batch.py`. `CHARGEBACK_FEE` is used by `handle_chargeback`.

Checks: `python -m unittest discover -s tests -t .` runs 5 tests and all pass. The removed functions had no references in the tests or elsewhere in the repository.

Comments: no comment elsewhere became false. The module docstring and the `routes.ini` note still hold. I did not commit, because this run is outside a git checkout.
