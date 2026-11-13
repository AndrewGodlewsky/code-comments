I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass and keeps the last update for each SKU:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    latest = {}
    for update in updates:
        # Popping first moves a repeated SKU to the position of its latest update.
        latest.pop(update["sku"], None)
        latest[update["sku"]] = update
    return list(latest.values())
```

The old version walked the feed backwards, then reversed the result twice. The new version returns the same updates in the same order. I checked this by hand on a sample feed with repeated SKUs, where the old and new code both return A1:4, C3:1, B2:9. The three existing tests pass (`python -m unittest tests.test_feed`).

The order of the result is the position of each SKU's latest update in the feed. Nothing in the tests, callers or docs says that order is required, so I kept it as it was and added a comment only on the non-obvious `pop`. If the order does not matter, the code could be simpler still. Please tell me if callers depend on it.

No other comments became false. The test comment about the later update winning still holds.
