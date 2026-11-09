I simplified `latest_updates` in `inventory/feed.py`. It now walks the feed once, front to back, and keeps the latest update per SKU in a dict. The old version reversed the list, filtered, then reversed twice more.

I kept the output order exactly as before: SKUs come out ordered by their last appearance in the feed. A plain `seen[sku] = update` would have been shorter, but it would order SKUs by first appearance, which changes the result for a feed like A1, B2, A1. So the loop pops the SKU before reinserting it. The comment in the code says why.

The existing tests pass, and I checked that the A1, B2, A1 case returns the same order as before. I made no other changes.
