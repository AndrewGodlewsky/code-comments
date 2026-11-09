I changed `write_batch` in `pipeline/stage.py` so each batch is written sorted by `customer_id`. I haven't run it, and there are no tests in the repository.

- **Sort key:** rows are cleaned first, then sorted on the trimmed `customer_id`. That is the value the loader receives. Sorting the raw ids could still leave the batch out of order after `clean()` trims them.
- **Comments:** I added a docstring saying the output is in ascending `customer_id` order. I also added a comment beside the sort explaining why it is there: the loader merge-joins in a single pass and silently skips out-of-order rows, and it can't be changed from this repository. It points to DATA-412.
- **Memory use:** `write_batch` now holds the whole batch in memory to sort it, where before it streamed row by row. That is fine unless batches are very large.
- **Sort order is unconfirmed:** I used Python's default string ordering. Ids are strings, so `"10"` sorts before `"9"`. If the loader compares ids in a different order, such as numeric, or case-insensitive or locale-aware, the sort key needs to change. Nothing I could read says which ordering the loader uses. Please confirm it.
