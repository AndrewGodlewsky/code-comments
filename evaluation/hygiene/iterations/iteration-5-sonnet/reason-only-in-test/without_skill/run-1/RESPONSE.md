I simplified `latest_updates` in `inventory/feed.py`. It now walks the feed once, front to back, and a later update for a SKU replaces the earlier one. The old version reversed the list twice and checked `if sku not in seen` along the way.

It returns exactly what it did before, including the order. The result is ordered by where each SKU last appears in the feed. A plain `latest[sku] = update` would have been shorter, but it would order results by first appearance, so I pop the SKU before reinserting it and added a one-line comment saying why.

The existing tests pass. They only check counts, not order, so nothing in them would catch an ordering change. If you don't care about order, you can drop the `pop` line.
