DATA-412: fixed in pipeline/stage.py.

`write_batch` now sorts each batch by `customer_id` before writing, so the warehouse loader's single-pass merge-join receives sorted input and no longer silently skips rows. The sort runs after `clean()`, so it orders by the trimmed id that is actually written. A comment at the point of the sort records the loader's ordering assumption and cites DATA-412.

Checked: a small batch with an iterator input, an untrimmed id (" 10 "), and out-of-order ids came out as 1, 10, 2 with cleaned emails. I did not run the loader or any test suite.

Things to confirm:
- The sort is plain string order, so "10" sorts before "2". If the loader compares ids in a different order (for example numerically), this fix will not match it. Please confirm the loader's comparison rule.
- The batch is now fully materialised in memory before writing. This is fine for normal batch sizes, but it is a change if batches can be very large.
- Rows with equal ids keep their input order (the sort is stable). I do not know whether the loader expects a particular tie-break, so I did not document one.
- The previous snapshot must also be in the same order for the merge-join to work. That is outside this file and was not checked.
