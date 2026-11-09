DATA-412: batches are now written sorted by customer_id.

What changed: `write_batch` in `pipeline/stage.py` now cleans each row, sorts the batch on the cleaned `customer_id` (the trimmed value that is written), and writes the rows in that order. A comment above the sort records why: the loader merge-joins in one pass and silently skips out-of-order rows (DATA-412). `clean()` is unchanged.

Checked: a stub sink with ids `" 10 "`, `"2"`, `"1 "` received them as `1, 10, 2`, with emails cleaned. I did not run the real loader, which lives in another repository.

Things to confirm:
- The sort is plain string order. `"10"` sorts before `"2"`. If the loader compares customer_id numerically, or with a different collation, this order will still be skipped. Please confirm the loader's comparison rule.
- Duplicate customer_ids keep their input order (the sort is stable). I have no evidence about which duplicate the loader expects, so I did not state a rule for it.
- The batch is now held in memory before writing, because a sort needs all rows. I have no figures for batch sizes, so I have not checked that this is acceptable at the largest batch size.
- The ticket is the only source for the loader's behaviour, so the comment cites DATA-412 for it. If the loader's requirement is documented elsewhere, that reference could be added.
- Nothing was committed.
