DATA-412: `write_batch` in `pipeline/stage.py` now writes each batch sorted by `customer_id`. I haven't run it or added a test.

- **Sort key:** rows are cleaned first and then sorted, so the order matches the trimmed ids the loader actually sees. Sorting the raw ids could misorder rows with leading whitespace.
- **Memory:** the sort holds the whole batch in memory. That should be fine for a staging batch, but say if batches can be very large.
- **Comment:** I added a short comment explaining why the sort is there: the external loader's single-pass merge-join silently skips out-of-order rows. Without it the sort looks removable.
- **Docstring:** I gave `write_batch` a docstring, since it had none and now has an ordering guarantee.
- **Sort order:** the ids are strings, so the sort is lexicographic. This is correct only if the loader and the previous snapshot order ids the same way.
