I simplified `latest_updates` in `inventory/feed.py`. The old version walked the feed backwards, collected the first sighting of each SKU into a dict, and then reversed the result to restore order. The new version is a single forward pass:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    latest = {}
    for update in updates:
        latest.pop(update["sku"], None)
        latest[update["sku"]] = update
    return list(latest.values())
```

Re-inserting a SKU after popping it moves it to the end of the dict, so the result keeps the same order as before: SKUs are listed by the position of their last update in the feed. The output is unchanged. I checked this against the original implementation on 20,000 random feeds, and the existing tests in `tests/test_feed.py` pass.

`total_units` and the docstring are untouched. No comments needed changing.

The tests do not assert the output order, so that ordering is currently covered only by my equivalence check. If callers depend on it, a test would be worth adding.
