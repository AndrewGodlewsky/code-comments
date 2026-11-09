DATA-412: staged batches are now written sorted by customer_id

What changed: `write_batch` in `pipeline/stage.py` now cleans every row, sorts the cleaned rows by `customer_id`, and then writes them to the sink. The sort runs after cleaning, so the order matches the trimmed ids the loader will see. Python's sort is stable, so rows with equal ids keep their original relative order. The `write_batch` docstring explains why the sort is there, because the loader merge-joins in a single pass and silently skips out-of-order rows. `clean` and its docstring were already accurate and are unchanged.

Check: a small in-memory run with ids `" 3 "`, `"1"`, `"2"` wrote them as `1, 2, 3`. I did not run a full warehouse load.

Limits: the sort is per batch, as the ticket asked. It does not order rows across batches, so if the loader needs the whole load in one sorted stream, that is a separate change. The ~3% of customers missing from last night's load are not restored by this change; they need a re-run of that load through the fixed stage.
