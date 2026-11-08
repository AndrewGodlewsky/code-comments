I simplified `latest_updates` in `inventory/feed.py`. It now builds a map from each SKU to the position of its last update, then returns those updates in that order:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    last_index = {update["sku"]: index for index, update in enumerate(updates)}
    return [updates[index] for index in sorted(last_index.values())]
```

The old version walked the list backwards, kept the first update seen for each SKU, then reversed the result twice. The new version returns the same updates in the same order: each SKU's latest update, ordered by where that update sits in the feed. I kept that order on purpose, so callers see no change.

Checks:
- The three existing unit tests pass.
- I compared the old and new versions on 5,000 random feeds (0 to 12 updates over five SKUs) and they returned identical results every time.

I left `total_units` and the tests unchanged.
