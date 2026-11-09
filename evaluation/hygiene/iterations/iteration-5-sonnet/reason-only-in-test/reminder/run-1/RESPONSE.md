I simplified `latest_updates` in `inventory/feed.py` to a single dict comprehension. Later updates overwrite earlier ones for the same SKU, so the last update per SKU wins, as before. The existing tests pass.

One behaviour change: the result used to be ordered by each SKU's last appearance in the feed. It is now ordered by each SKU's first appearance. Nothing in the repo depends on the order (the tests and `total_units` ignore it), but tell me if a caller outside it does.

On comments, I added a line to the docstring saying why the last update wins: a SKU sent again later is a correction. Before, that reasoning only appeared in a test comment. No existing comment became false.
