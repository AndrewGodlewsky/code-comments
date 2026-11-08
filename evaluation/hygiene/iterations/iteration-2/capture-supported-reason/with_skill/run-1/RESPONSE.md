DATA-412: fix applied in pipeline/stage.py

`write_batch` now cleans every row first, then writes the batch sorted by the cleaned `customer_id`. The loader's single-pass merge-join therefore receives sorted input, and out-of-order rows can no longer be silently skipped. I added a comment at the sort explaining why the ordering is required.

Checks:
- A quick run with three out-of-order rows (one with a padded id) wrote them as `1`, `2`, `3`, with emails still lower-cased.
- I did not run the full pipeline or compare against last night's load.

Open points:
- Sorting uses Python's default string order. If the warehouse loader compares customer_id with a different collation (for example numeric, or case-insensitive), the order needs to match it. Please confirm with the loader's owners.
- The batch is held in memory to sort it. That is fine for batch-sized inputs; tell me if batches can be very large.
- The fix covers batches written through `write_batch`. Any other path that feeds the loader needs the same ordering.
