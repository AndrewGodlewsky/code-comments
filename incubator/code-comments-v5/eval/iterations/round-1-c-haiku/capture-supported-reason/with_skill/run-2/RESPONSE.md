DATA-412 is fixed on our side in `pipeline/stage.py`. `write_batch` now sorts each batch by `customer_id` before writing it, so the warehouse loader's single-pass merge-join receives rows in order and no longer skips any.

What changed:
- `write_batch` cleans all rows first, sorts them by the cleaned `customer_id` (ascending, Python's default string order), and then writes them to the sink.
- The sort runs after `clean()`, because the loader sees the trimmed id. Sorting the raw values could place rows differently from the order the loader reads.
- The docstring records the loader's ordering requirement and points to DATA-412, so the constraint stays next to the code.

Please check before relying on this:
- Ordering is plain string order. I smoke-tested it with the ids `' 9 '`, `'10'` and `'2 '`, and it wrote them as `10, 2, 9`. If the loader compares `customer_id` numerically, or with a different collation, this order will still be skipped. Confirm the loader's comparison rule against its code in the other repository. I did not change the sort key because nothing in this repository says which rule the loader uses.
- The whole batch is now held in memory before writing, where it was previously streamed row by row. This is fine for normal batch sizes, but it matters if a batch can be very large.
- There are no tests in this repository for `pipeline/`, so I checked the change only with the smoke test above.
- `pipeline/__init__.py` is empty and was left unchanged.
