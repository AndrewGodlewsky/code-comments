I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update re-inserts its SKU into a dict, so the last update for each SKU wins. The old version walked the feed backwards and reversed the result twice. The return value is unchanged, including order: results are ordered by each SKU's last update position in the feed. I added a one-line comment on the pop-and-reinsert step, because a later editor who removes it would silently change that order.

I checked the rewrite against the original on 20,000 random feeds and the outputs matched exactly. The three existing tests in `tests/test_feed.py` pass.

Gap for you: no test or doc in the inputs says the output order matters, and I found no recorded reason for it. If callers depend on that order, add a test that pins it. If they do not, the order could be dropped and the pop line removed.
