DATA-412: staging batches are now written sorted by customer_id.

What changed: `write_batch` in `pipeline/stage.py` now cleans every row, sorts the cleaned rows by `customer_id`, and then writes them to the sink. Rows that arrive out of order no longer reach the warehouse loader in that order, so its single-pass merge join should stop skipping them.

Details:
- The sort runs after `clean()`, because `clean()` trims `customer_id`. Sorting before trimming could put rows in the wrong order for the value that is actually written.
- The sort is a string sort on the trimmed id. I checked a small batch: `' 9 '`, `'10'`, `'2'` come out as `'10'`, `'2'`, `'9'`. If the loader compares customer_id numerically or with a different collation, this order will not match it. Please confirm the loader's comparison rule before this ships.
- Each batch is sorted on its own. If the loader expects the whole load to be sorted across batches, this change is not enough.
- The batch is now held in memory in full before it is written, because sorting needs every row. Batch size matters for memory use.
- The comment above the sort explains why the order matters. The `clean()` and module docstrings are still accurate, so I left them alone.

Verification: I ran `write_batch` on a three-row batch and confirmed the output order. The repository has no test suite, and I did not run the warehouse loader, so the fix has not been checked against the real loader or against last night's data.

Git: nothing was committed, pushed or otherwise changed in git. The only file edited is `pipeline/stage.py`. This message is in `RESPONSE.md`.
