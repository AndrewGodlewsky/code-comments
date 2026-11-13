I did not simply drop the ordering, because something does need it: `reconcile()` in `ledger/reconcile.py` is a merge join that walks the ledger and bank lists in step, and its comment says `fetch_rows` supplies the ledger side in id order. Unsorted rows would silently produce wrong matches (rows reported as unmatched on both sides). `write_rows` in `csv_out.py` does not care about order, which is probably what you saw.

What I changed instead: removed the Python `rows.sort(...)` in `fetch_rows` and added `ORDER BY id` to the query. `id` is the primary key, so SQLite can return rows in order from the index, with no Python-side sort. The order is the same as before, and I documented it in the `fetch_rows` docstring.

I ran the existing tests and they pass. I did not time it on a large ledger, so please check the speedup against your profile. If the nightly CSV export is the only slow caller, you could add an unordered variant for it, but I haven't done that.
