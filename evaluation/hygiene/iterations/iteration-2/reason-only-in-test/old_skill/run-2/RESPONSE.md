I simplified `latest_updates` in `inventory/feed.py`. It no longer walks the list backwards and reverses the result twice. It now makes one forward pass, using a dict where each SKU is removed and re-inserted so it sits at its latest update's position:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    latest = {}
    for update in updates:
        # Re-inserting moves the SKU to the end, so output follows each SKU's latest update.
        latest.pop(update["sku"], None)
        latest[update["sku"]] = update
    return list(latest.values())
```

The output is unchanged. It still returns one update per SKU, the last one in the feed, in the same order as before. I checked this against the original implementation on 5,000 random feeds, and the existing tests pass (3 of 3). `total_units` and the docstring are untouched. The one new comment explains the pop-and-reinsert step, since that line looks odd and a future editor might remove it and change the output order.

Nothing is committed.
