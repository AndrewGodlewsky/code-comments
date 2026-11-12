DATA-412: `write_batch` in `pipeline/stage.py` now sorts each batch by the cleaned `customer_id` before writing it.

Change: `write_batch` cleans all rows, sorts them by `customer_id` (after the trim, since the trim is part of the id the loader sees), and then writes them in that order. I left `clean` unchanged. The new comment above the sort records the loader's single-pass merge-join and the silent skip on out-of-order rows, with DATA-412 as the pointer.

I ran a quick check on three sample rows with ids `' 9 '`, `'10'` and `'2'`. The output order was `['10', '2', '9']`, which confirms the sort runs and uses the trimmed value.

Open questions for you:
- The sort is plain string order, so `'10'` sorts before `'2'`. That is correct only if the loader and the previous snapshot also compare `customer_id` as strings. If the loader treats ids as numbers, or uses another collation, the batch will still be skipped on those rows. Please confirm the loader's comparison rule. I could not verify it from this repository.
- The sort buffers the whole batch in memory. That is fine for normal batch sizes but worth knowing for very large ones.
- Ties on `customer_id` keep their input order, because Python's sort is stable. I did not check whether the loader needs a particular order among duplicate ids.
- The 3% loss was not reproduced here. Only the ordering fix is verified, and only on sample data.
