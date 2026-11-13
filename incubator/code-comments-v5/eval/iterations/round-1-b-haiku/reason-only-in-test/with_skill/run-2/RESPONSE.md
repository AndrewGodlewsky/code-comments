I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass, popping and reinserting each SKU so the dict holds the last update per SKU in feed order, instead of walking the feed backwards and reversing the result twice.

The output is unchanged. The last update for each SKU still wins, and the SKUs are still ordered by where each SKU's last update sits in the feed. The pop-then-reinsert line is commented because a plain `latest[sku] = update` would keep each SKU at its first position and change the order.

The three existing tests pass (`python -m unittest tests.test_feed`). I also checked the new version against the old logic on a mixed feed and got the same output, including order.

Notes:
- No existing test checks the output order, so that ordering is currently unpinned. If you rely on it, a test would protect it. I did not add one because you asked only for a simplification.
- I did not change `total_units`, the tests, or the module docstring. No comment became false.
