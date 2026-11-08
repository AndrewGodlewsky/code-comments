DATA-412: staging batches are now written sorted by customer_id

The warehouse loader merge-joins each batch against the previous snapshot in one pass, so any row that arrives out of order is silently skipped. That explains the roughly 3% of customers missing from last night's load. Since we can't change the loader, `write_batch` in `pipeline/stage.py` now sorts each batch by `customer_id` before writing it.

What changed:
- `write_batch` cleans every row first, then sorts the cleaned rows by `customer_id` and writes them in that order. The sort uses the cleaned (trimmed) id, because trimming can change where a row falls in the order.
- Accepting any iterable still works, because the batch is materialised into a list before sorting.
- `clean` is unchanged.

Checked: a small batch with a padded id (`" 10 "`, `"9"`, `"2"`) was written in sorted order (`10`, `2`, `9`). I did not run the loader or a full load.

Open point: the sort is plain string order, which is what the loader will see if `customer_id` is a text column. If the loader compares ids numerically, or the ids are not zero-padded, the order we write may not match its expectation. Please confirm the loader's comparison rule for this column. If it is numeric, the sort key in `stage.py` needs to change to match.
