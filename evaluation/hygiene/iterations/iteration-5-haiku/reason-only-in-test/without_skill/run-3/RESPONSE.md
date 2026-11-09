I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass over the feed: for each update it removes any earlier entry for that SKU and records the new one, so each SKU ends up holding its last update, in the order those last updates appear. The old version walked the list backwards, built a dict, and reversed the result twice to get the same order.

```python
def latest_updates(updates):
    """Return the last update for each SKU, ordered by where that update sits in the feed."""
    latest = {}
    for update in updates:
        latest.pop(update["sku"], None)  # re-insert so the SKU moves to its latest position
        latest[update["sku"]] = update
    return list(latest.values())
```

Behaviour is unchanged. The existing tests pass (3 of 3), and I checked the new function against the original logic on 20,000 random feeds, with identical output each time, including ordering. `total_units` and the rest of the module are untouched.

Nothing was committed.
