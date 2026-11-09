I simplified `latest_updates` in `inventory/feed.py` to a single dict comprehension. Later entries overwrite earlier ones for the same SKU, so the last update per SKU still wins. The tests pass.

I added a short comment saying that the last update wins and why: the warehouse corrects a miscount by resending the SKU later in the same feed. The old reversed-loop shape was the only visible sign of that rule, and the reason comes from `tests/test_feed.py`.

One behaviour change: the returned list is now ordered by each SKU's first appearance in the feed. Before, it was ordered by each SKU's last appearance. Nothing in the tests or in `total_units` depends on the order. If a caller does, tell me and I'll restore the old ordering.
