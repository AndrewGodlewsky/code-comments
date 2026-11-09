DATA-412: `write_batch` in `pipeline/stage.py` now writes each batch sorted by `customer_id`. I haven't run it or added a test.

The loader's single-pass merge-join skips rows that arrive out of order, which fits the roughly 3% of customers that went missing. Since we can't change the loader, I did the fix on our side. Rows are cleaned first and then sorted on the trimmed id, so the sort key is the same value that gets written. Sorting on the raw id could leave whitespace-padded ids out of order.

- **Sort order:** Ids are strings, so the sort is lexicographic ("10" sorts before "9"). That's correct only if the loader's snapshot is ordered the same way. If it expects numeric order or a particular collation, the key needs to change. Please confirm the loader's ordering.
- **Memory:** The whole batch is now held in memory to sort it, instead of streaming. That's fine for normal batch sizes but worth knowing if batches are very large.
- **Duplicates:** I didn't deduplicate, and Python's sort is stable, so duplicate ids keep their input order.
- **Backfill:** The customers dropped last night won't reappear on their own. They need the affected batch re-staged and reloaded.
