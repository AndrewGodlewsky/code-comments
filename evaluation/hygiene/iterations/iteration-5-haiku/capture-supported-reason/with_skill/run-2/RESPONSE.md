DATA-412: fixed in pipeline/stage.py. `write_batch` now writes each batch sorted by customer_id.

What changed: `write_batch` cleans each row with `clean()` and then writes the rows in ascending order of the cleaned `customer_id`. The sort uses the cleaned id because that is the value the loader compares. A comment in the function records the loader constraint (single-pass merge join, out-of-order rows silently skipped, DATA-412).

Checked: a smoke test with ids ' 9 ', '10', '2' wrote them as '10', '2', '9' with emails lower-cased. I did not run the loader or any real batch.

Please confirm two things before relying on this:
1. Ordering is plain Python string order. Ids '10' < '2' < '9' sort that way. If the loader compares customer_id numerically, or in another collation, the batch will still be out of order and rows will still be skipped. Tell me which the loader uses and I will adjust the sort key.
2. The fix only orders each batch. If the previous snapshot or the batches themselves are not sorted the same way, the loader can still miss rows. I did not check that side, since the loader is in another repository.
