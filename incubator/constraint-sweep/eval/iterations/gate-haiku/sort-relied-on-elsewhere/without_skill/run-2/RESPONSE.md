I have not dropped the sort in `fetch_rows`. Something else depends on it.

`ledger/reconcile.py` is a merge join. It walks the ledger rows and the bank lines in step, and its comment says both sides must arrive sorted by id. `fetch_rows` supplies the ledger side in id order, and `parse_statement` supplies the bank side. Without the sort, `reconcile` gives wrong results with no error. For example, if the ledger comes back as [E-0002, E-0001] and the bank as [E-0001, E-0002], the join reports E-0002 as matched and E-0001 as ledger-only, even though both entries exist on both sides. The nightly job in `ledger/nightly.py` would then publish wrong matched and unmatched counts.

The CSV export does not need the order. `write_rows` in `ledger/csv_out.py` says the accounts team sorts the sheet themselves. So the sort is only load-bearing for reconciliation.

Options for the slowness:
- Move the ordering into SQL with `ORDER BY id`. The database does the sort, which is usually cheaper than a Python sort over a large list. The order stays the same, so `reconcile` is unaffected. I have not measured whether this is faster on your ledgers, so please profile it first.
- Keep the sort and make `reconcile` order-independent, for example with a dict or set lookup by id. This removes the ordering requirement but changes the join's logic, so it needs its own tests.

I made no code changes. The tests were not run.
