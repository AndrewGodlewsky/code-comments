DATA-412: fixed in `pipeline/stage.py`. `write_batch` now cleans every row first and then writes the batch sorted by `customer_id`. The loader's merge-join should no longer skip rows because they arrived out of order.

- **Sort key:** I sorted on the cleaned (trimmed) id, because that is the value the loader sees. Sorting on the raw id could leave a batch out of order after trimming.
- **Memory:** the whole batch is now held in memory so it can be sorted. That is fine unless batches are very large.
- **Ordering assumption:** `customer_id` is a string here, so the sort is lexicographic (`"10"` comes before `"9"`). If the loader compares ids numerically, or uses a different collation, this order will not match it. I couldn't see the loader, so please confirm which ordering it expects.
- **Testing:** I haven't run or tested this. There was no test suite in the repo.
- **Missing customers:** the ~3% already missing from last night's load will need a re-run of that batch.
