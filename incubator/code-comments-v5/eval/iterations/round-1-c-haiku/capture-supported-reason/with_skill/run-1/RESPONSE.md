I changed `write_batch` in `pipeline/stage.py` so each batch is written sorted by `customer_id` (DATA-412).

What changed:
- `write_batch` now cleans every row first, sorts the cleaned rows by `customer_id`, and then writes them in that order.
- The sort runs after `clean()`, so the order matches the trimmed id that is actually written. Sorting the raw ids could give a different order when ids have stray whitespace.
- I added a comment above the code. It records the loader's single-pass merge-join, its silent skipping of out-of-order rows, the ticket id, and the fact that the loader lives in another repository.

Things to know:
- The sort is stable, so rows with equal `customer_id` keep their arrival order. I did not find evidence of how the loader treats duplicate ids, so I have not written a rule about them.
- The whole batch is now held in memory before it is written. If batches can be large, that is worth checking.
- I checked the change with one quick run: three unsorted rows, one with a padded id, came out as ids 1, 2, 3. The repository has no test suite, and I have not run the real loader against the output.
- I did not use git, so nothing is committed.
