DATA-412: batches are now written sorted by customer_id

I changed `write_batch` in `pipeline/stage.py` so each batch is cleaned, sorted by the cleaned `customer_id`, and then written to the sink. The warehouse loader's single-pass merge-join can now rely on sorted input, so out-of-order rows no longer get silently skipped on our side.

What changed:
- `write_batch` collects the cleaned rows, sorts them by `customer_id` (stable sort), then writes them. `clean()` and the sink interface are unchanged.
- The sort key is the cleaned id, since that is the value the loader sees.

Checked:
- With a fake sink and ids `' 30 '`, `'10'`, `'20 '`, the output order is 10, 20, 30, with each email kept on its own row.
- I did not run the full pipeline or the warehouse loader, and the repo has no test suite.

Trade-offs to know about:
- The batch is now held in memory before writing. This is fine for normal batch sizes, but a very large batch would need more memory than before.
- If the batch contains duplicate `customer_id` values, they will still be passed through in sorted order. Nothing here de-duplicates them.

I did not read `SKILL.md` from the code-comments workspace, as the task said to stay inside this repository.
