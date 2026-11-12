I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update overwrites the SKU's entry, and the result is the dict's values. The old version walked the feed backwards and then reversed the result twice to get the same output.

Behaviour is unchanged. The three existing tests pass, and the old and new versions agree on 20,000 random feeds, including the output order.

The one non-obvious detail is ordering. Results follow the feed position of each SKU's winning (latest) update, so a re-sent SKU moves to the end. The new code does this with `pop` before the assignment, and a comment beside it says why. The docstring now states the replacement rule and the ordering.

I did not change the tests. No existing test checks the output order, so a test pinning that order would be a useful follow-up if callers depend on it. I did not find a reason for the order in the tests or docs, so I did not record one. If you know why callers need that order, tell me and I will add it to the code.
