I fixed DATA-412 on our side in `pipeline/stage.py`. `write_batch` now cleans every row, sorts the cleaned batch by `customer_id`, and then writes it to the sink. The sort runs after `clean()` because the loader compares the trimmed id, so sorting before trimming could order rows by stray whitespace. I added a short comment above the sort that records the loader's single-pass merge-join and its silent skipping of out-of-order rows, with DATA-412 as the pointer.

Things to check:

- The sort uses Python's default string ordering on `customer_id`. If the loader orders ids differently (for example numerically, or with a case-insensitive collation), the batch will still be out of order for it. Please confirm the loader's comparison rule.
- `write_batch` now reads the whole batch into memory before writing. This was needed for sorting, and it matters only if batches are very large.
- The fix only orders each batch. It does not change the previous snapshot the loader joins against, so if that snapshot is not sorted the problem remains.
- I did not run tests or load the data. Nothing in the repository exercises `write_batch`, and the loader is in another repository.
- `pipeline/__init__.py` is empty and I left it unchanged.
