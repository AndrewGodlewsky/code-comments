DATA-412: `write_batch` now writes each batch sorted by cleaned `customer_id`.

Change, in `pipeline/stage.py`:
- `write_batch` runs `clean()` on every row, sorts the cleaned rows by `customer_id`, then writes them to the sink in that order.
- The sort uses the trimmed id that is written, not the raw input value. The loader joins on the stored value, so sorting before `clean()` could misorder ids that carry stray whitespace.
- The function docstring records the ordering contract and the reason for it (the loader's single-pass merge-join that skips out-of-order rows, DATA-412).

Trade-off: `write_batch` now materialises the whole batch in memory before writing. The previous version streamed rows one at a time. For staging batches that fit in memory this is fine. If batches can grow very large, this would need a different approach, such as an external sort.

Verification: I ran a small check with three out-of-order rows, one with a leading space in the id. Output was ids `1, 2, 3` in order, with emails lower-cased. There is no test suite in this directory, so I did not add tests.

Not verified: the loader itself lives in another repository, so I did not confirm its join behaviour. The fix relies on the ticket's description of it.

Nothing was committed. No git or task-tracking actions were taken, per the instructions for this run.
