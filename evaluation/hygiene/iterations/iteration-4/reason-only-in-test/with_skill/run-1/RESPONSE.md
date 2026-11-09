I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update overwrites the SKU's entry, and the SKU is moved to the end first so the output order matches the old function. The old version walked the feed backwards, kept the first sighting of each SKU, and reversed the result twice to restore order. The change is inside the function only; `total_units` and the public signatures are untouched.

The three existing tests pass. I also compared the old and new implementations on 2,000 random feeds, including the output order, and they matched.

Two things to check:
- The output order is the order of each SKU's last update in the feed. Nothing in the tests or docs says that order matters. If it doesn't, the function can be a plain `{u["sku"]: u for u in updates}.values()`, which orders by first appearance. That would be a further simplification, but it changes the returned order, so I left it alone.
- The "later update wins" rule is what the test `test_later_update_wins` describes, and the new loop shows it directly. I added no comment, since nothing I read gives a reason for the pop-and-reinsert ordering.
