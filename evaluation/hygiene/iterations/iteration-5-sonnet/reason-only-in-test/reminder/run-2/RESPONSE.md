I simplified `latest_updates` in `inventory/feed.py`. It now walks the feed once, front to back, and each SKU's later update replaces the earlier one. That removes the two `reversed` calls and the `if sku not in seen` check.

Behaviour is unchanged, including the result order. SKUs still come back in the order of their last update. I used `pop` before the assignment so a repeated SKU moves to its new position. A plain `{sku: update}` overwrite would have kept the first position and changed that order.

The existing tests pass. I added no comments and changed none. The docstring and the comment in the tests are still accurate.
