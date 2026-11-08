I simplified `latest_updates` in `inventory/feed.py`. It now makes one pass to record the last index of each SKU, then keeps the updates whose index matches that last index:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    last_index = {update["sku"]: i for i, update in enumerate(updates)}
    return [update for i, update in enumerate(updates) if last_index[update["sku"]] == i]
```

The behaviour is unchanged. The result keeps the last update for each SKU, in the order those last updates appear in the feed. The old reverse-and-reverse-again dance produced that same order, and I kept it on purpose. A plain `{sku: update}` dict would have ordered SKUs by their first appearance instead, so it is not a drop-in replacement.

Checks:
- The existing unit tests in `tests/test_feed.py` pass (3 tests).
- I compared the new and old implementations on 2,000 random feeds with up to 12 updates over four SKUs. They returned identical lists every time.

I did not change any comments or docstrings, and I did not touch other files. I did not commit anything.
