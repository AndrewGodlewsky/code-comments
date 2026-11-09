I simplified `latest_updates` in `inventory/feed.py`.

The old version walked the feed backwards, kept the first update seen for each SKU, then reversed the result to restore feed order. The new version walks the feed forwards and, for each update, removes any earlier entry for that SKU before inserting the new one. A plain dict then holds each SKU's last update, ordered by where that last update sits in the feed. That is the same output order the old code produced, so callers see no change.

I also updated the docstring to state the ordering, since it is part of the contract. The `total_units` docstring is still accurate and was left alone.

The three existing tests in `tests/test_feed.py` pass (`python -m unittest tests.test_feed`). I did not add new tests, because the existing ones already cover last-update-wins, one-per-SKU and totals.
