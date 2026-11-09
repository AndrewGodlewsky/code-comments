I simplified `latest_updates` in `inventory/feed.py`. It now builds a map from each SKU to the position of its last update, then keeps the updates that sit at those positions:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    last_position = {update["sku"]: i for i, update in enumerate(updates)}
    return [update for i, update in enumerate(updates) if last_position[update["sku"]] == i]
```

The old version walked the feed backwards, tracked the first sighting of each SKU, and reversed the result twice. The new version does the same job in two passes without the reversals.

Behaviour is unchanged. The output keeps the same order: each SKU's final update, ordered by where that update appears in the feed. The unit tests pass (3 of 3). I also compared the old and new implementations on 2,000 random feeds and they returned identical lists.

The docstring still describes the function accurately, so I left it alone. No other comments or docs needed changes.
