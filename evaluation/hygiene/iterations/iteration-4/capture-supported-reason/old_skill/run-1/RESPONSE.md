DATA-412: out-of-order customer rows in the warehouse load

I changed `write_batch` in `pipeline/stage.py` so each batch is cleaned, sorted by `customer_id`, and then written. The warehouse loader is untouched.

The sort key is the cleaned id (the trimmed value that `clean()` produces), because that is the value the loader compares. Sorting on the raw id would misorder values with stray whitespace. Rows with the same id keep their input order, since Python's sort is stable.

I added a comment above the change recording why the order matters: the loader merge-joins in one pass and silently skips out-of-order rows.

I checked the change with one small batch whose ids arrive as " 3 ", "1" and "2 ". It was written as 1, 2, 3. I did not run it against the real loader, and the repository has no test suite.

Things to be aware of:
- Each batch is now held in memory while it is sorted. This is fine for batch-sized input, but it would matter if a batch were very large.
- Sorting uses Python's default string ordering. If the loader orders ids differently (for example, a database collation that is case-insensitive or numeric-aware), some rows could still be out of order. Please confirm the loader's ordering rule against the ids in last night's batch.
- The fix only covers batches written by this code path. Rows that reach the loader from anywhere else are not sorted.
