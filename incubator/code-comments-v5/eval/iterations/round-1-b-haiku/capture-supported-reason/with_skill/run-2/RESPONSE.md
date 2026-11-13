I changed `write_batch` in `pipeline/stage.py` so each batch is written sorted by `customer_id`, which addresses DATA-412.

What changed: `write_batch` now cleans every row first, sorts the cleaned rows by their trimmed `customer_id`, and then writes them in that order. Sorting happens after cleaning because the loader joins on the cleaned value. A comment above the sort records the reason (the loader's single-pass merge join skips out-of-order rows) and points to DATA-412.

Things to check:
- The loader is in another repository and I could not read it. I relied on the ticket's claim that it expects `customer_id` order and skips out-of-order rows. I did not verify the comparison it uses. This change uses plain Python string ordering. If the loader compares differently (for example numerically, or case-insensitively), the key needs to change to match.
- `write_batch` now reads the whole batch into memory before writing, because a sort needs every row. Large batches will use more memory than before.
- `pipeline/__init__.py` is empty and the repository has no tests, so I did not run anything. A quick check would be to pass a shuffled batch with padded ids to a list-backed sink and confirm the written order.
- I did not commit, because this task excluded git.
