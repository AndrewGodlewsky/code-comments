DATA-412: staging batches are now written sorted by customer_id

The fix is in pipeline/stage.py. `write_batch` previously cleaned and wrote rows in arrival order, which is what let out-of-order rows reach the warehouse loader's single-pass merge-join. It now cleans every row in the batch, sorts the cleaned rows by `customer_id`, and then writes them.

The sort uses the trimmed `customer_id`, because that is the value the loader joins on after cleaning. Rows are sorted within each batch only, which is what the loader requires.

I checked the change with a small in-memory test: rows with ids " 3 ", "1" and "2" came out as 1, 2, 3 with their emails lower-cased. I did not run the real loader or the pipeline against real data, since neither is in this repository.

Two things to be aware of:
- `write_batch` now holds the whole batch in memory before writing. That is fine for batch-sized inputs, but it would matter if a batch were ever very large.
- Rows with the same `customer_id` keep their arrival order, since Python's sort is stable. I did not add a tie-breaker.

I did not read the code-comments SKILL.md that the request asked me to read first, because the same request also said not to read anything outside this repository. If you want that skill applied, let me know and I can read it.
