DATA-412: fixed on our side in `pipeline/stage.py`.

The cause is that the warehouse loader merge-joins each batch against the previous snapshot in one pass and silently skips rows that arrive out of order. `write_batch` wrote rows in the order it received them, so any batch that was not already sorted by customer_id lost rows. I changed `write_batch` so it cleans every row and then sorts the batch by the cleaned `customer_id` before writing. I sort after cleaning because the loader sees the trimmed id. The sort is stable, so duplicate ids keep their input order. The function signature and the `clean` function are unchanged.

I checked the change with one small hand-run sample (ids ' 9 ', '10', '2' came out as '10', '2', '9'). I did not run it against real batches or the loader.

One thing to confirm: the sort is by string value, so '10' sorts before '2'. That is correct only if the loader compares customer_id as text. If the loader compares ids as numbers, this sort will still lose rows, and the sort key should become `int(customer_id)` (assuming every id is numeric). Please check this against the loader before the next load.

Nothing was committed, and nothing outside this repository was read or changed.
