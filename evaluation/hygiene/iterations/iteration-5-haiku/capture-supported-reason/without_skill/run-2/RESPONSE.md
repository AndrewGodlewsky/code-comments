DATA-412: warehouse batches are now written sorted by customer_id

The warehouse loader merge-joins each staging batch against the previous snapshot in one pass and silently skips rows that arrive out of order. I changed `write_batch` in `pipeline/stage.py` so every batch is written sorted by customer_id:

- Each row is cleaned first (`clean` trims customer_id and lower-cases email), then the batch is sorted on the cleaned customer_id. Sorting on the cleaned value matters because the loader compares the id as it is written, so a leading space would otherwise change the order.
- The sort is a plain string sort, since customer_id is a string. I checked a small sample: ids `' 10 '`, `'2'`, `'1'` come out as `'1', '10', '2'`. The loader must also compare these as strings. If it compares numerically, the sort key will need to change to match.
- The batch is held in memory before writing, because a sort needs every row. For large batches this costs memory. If batches get big, the next step would be an external sort.

I did not run the loader or the full pipeline, since the loader is in another repository. I only ran `write_batch` on a small sample. Nothing has been committed.

Still open: the rows that were skipped in last night's load are not repaired by this change. They need a re-run of that batch through the fixed stage, or a backfill against the snapshot.
