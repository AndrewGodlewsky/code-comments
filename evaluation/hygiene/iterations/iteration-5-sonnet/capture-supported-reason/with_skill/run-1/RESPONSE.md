DATA-412 is fixed on our side in `pipeline/stage.py`. I haven't run it or added tests.

`write_batch` now cleans every row first, then sorts the batch by the cleaned (trimmed) `customer_id` and writes the rows in that order. I sort after cleaning because the loader sees the trimmed ids. Sorting the raw ids could still put rows out of order.

I added a docstring and a short comment explaining why the sort is there. They say the loader single-pass merge-joins on `customer_id` and silently skips out-of-order rows, and that the loader is in another repo so the order has to be guaranteed here. The comment cites DATA-412 after that explanation.

- **Sort order:** the sort is plain ascending string order on `customer_id`. I don't know the loader's exact collation, for example whether it compares case-sensitively or treats ids as numeric strings. If it differs from Python's default string order, the sort key needs to match it. Can you confirm?
- **Memory:** `write_batch` now holds the whole batch in memory to sort it, where before it streamed. That should be fine for batches of normal size, but tell me if they are very large.
