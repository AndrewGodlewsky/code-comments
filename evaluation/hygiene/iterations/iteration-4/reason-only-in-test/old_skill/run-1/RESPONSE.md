I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update for a SKU removes the earlier entry and is inserted at the end, and the function returns the dict's values. The old version walked the feed backwards, collected first-seen entries and reversed the result twice.

The output is unchanged. The three existing tests pass, and I checked the old and new versions against each other on 20,000 random feeds with identical results, including order.

I added a short comment at the point of the rule. It records that a later update replaces an earlier one because the warehouse resends a SKU to correct a miscount. The reason comes from the existing test `test_later_update_wins`.

Two things need your input:
- The result is ordered by each SKU's last update, not by first appearance. The rewrite keeps that order. Nothing in the tests or docs says whether any caller depends on it. If nothing does, the order could be made simpler still. If something does, that reason should be written beside the code, and I have not guessed one.
- I did not change `total_units`, which still calls `latest_updates`.
