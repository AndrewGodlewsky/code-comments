I have not dropped the sort in `fetch_rows`, because something does depend on it.

`ledger/reconcile.py` pairs ledger rows with bank statement lines using a merge join. It walks both lists in step, and its comment says both sides must arrive sorted by id. `fetch_rows` supplies the ledger side in id order. If the sort is removed, `reconcile` gives wrong results. I checked this with a small unsorted ledger (E-0003, E-0001, E-0002) against a sorted bank statement that has all three matching entries. It reported 1 matched, 2 ledger-only and 2 bank-only, when all three should match. The nightly job in `ledger/nightly.py` calls `reconcile(fetch_rows(conn), ...)`, so it would silently produce bad counts every night.

The existing tests would not catch this. `test_returns_every_entry` only compares sets of ids, and nothing tests `reconcile` with unsorted input.

The `ORDER BY` is not the only thing that could be slow, though. Some options:

1. Move the ordering into the SQL query (`SELECT ... FROM entries ORDER BY id`) and remove the Python sort. The database can often do this with an index on `id`, which is usually faster than sorting in Python. This needs a benchmark on a real big ledger before it counts as a speedup.
2. Make `reconcile` independent of order. Build a dict of bank lines keyed by id and look up each ledger row. This removes the ordering requirement from the join and would also let `fetch_rows` drop the sort. The cost is one hash lookup per row and some extra memory.
3. Keep the sort but measure it first. Profiling may show that the time is actually spent elsewhere in `fetch_rows`, such as building the `Row` objects.

The CSV export (`ledger/csv_out.py`) does not need order, so the sort can be dropped from that path without any effect on reconciliation.

I have made no code changes. Tell me which option you want, and I will make it and add a test that checks `reconcile` with unsorted ledger input.
