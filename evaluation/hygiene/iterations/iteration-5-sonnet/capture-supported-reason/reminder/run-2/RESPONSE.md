DATA-412: `write_batch` in `pipeline/stage.py` now cleans every row and writes them sorted by `customer_id`. The loader's single-pass merge-join then sees ordered input, so rows should no longer be skipped.

- The sort uses the trimmed id, because that is the value the loader receives. Sorting on the raw id could still produce out-of-order output when ids have stray whitespace.
- The sort is lexicographic on the string id. This is only correct if the loader's snapshot is ordered the same way (string order, not numeric). Please confirm that with the loader's owners.
- I added a docstring and a short comment explaining why the sort is there, since the reason is not obvious from the code. No existing comments became false.
- Because the whole batch is sorted in memory, a very large batch will use more memory than before.
- I did not run it or add tests; the repository has none.
