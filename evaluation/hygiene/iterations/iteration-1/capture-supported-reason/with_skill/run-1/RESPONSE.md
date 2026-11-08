DATA-412: staging batches are now written sorted by customer_id

I changed `write_batch` in `pipeline/stage.py` so each batch is cleaned, sorted by the cleaned `customer_id`, and then written. The loader's single-pass merge join should now receive rows in order, so the rows it was silently skipping should be written correctly. I did not change the loader, which lives in the other repository.

What changed:
- `write_batch` now materializes the cleaned rows and sorts them on the cleaned `customer_id` (the value that is actually written), then writes them in that order.
- A comment above the function records the constraint: the loader merge-joins in one pass and silently skips out-of-order rows, so the sort key is the cleaned id.

Checks:
- I ran `write_batch` on a small unsorted sample with an untrimmed id (`' 3 '`). The output came out as ids `1, 2, 3`, with emails lower-cased.
- I did not run the warehouse loader or a full pipeline run, and I have no access to the loader's code.

Things to be aware of:
- Sorting holds each batch in memory before writing. If batches are large, that is a memory cost to check.
- The sort uses Python's default string ordering. I could not confirm that the loader compares ids the same way. If it orders them differently (for example numerically, or case-sensitively against a different collation), the fix will not hold. This should be confirmed against the loader before relying on it.
- The sort is stable, so rows with equal ids keep their input order. I did not add any deduplication, and the ticket does not say whether duplicate ids can occur in a batch.
- The ticket's account of the ~3% loss is the basis for the fix. I did not reproduce the missing rows from last night's data.
