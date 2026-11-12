I removed two functions from `events/handlers.py` that nothing calls any more:

- `handle_refund_v1`. The 1.3.0 changelog entry replaced it with `handle_refund` and says the `refund_v1` kind is no longer accepted. `config/routes.ini` does not list it, so `dispatch` never reaches it.
- `format_old_receipt`. The 1.2.0 changelog entry says receipts moved to the billing service and this function is no longer used here. No code or test references it.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, and `CHARGEBACK_FEE`. `dispatch.py` reaches the three handlers by name through `handle_<kind>`, and `config/routes.ini` switches on the `refund`, `chargeback` and `payout` kinds. `CHARGEBACK_FEE` is used by `handle_chargeback`.

The unit tests pass (5 tests, OK). I left `CHANGELOG.md` alone because its entries are history. No comments in the remaining code became false, so no comment edits were needed. I did not commit or push, since you asked me not to use git here.
