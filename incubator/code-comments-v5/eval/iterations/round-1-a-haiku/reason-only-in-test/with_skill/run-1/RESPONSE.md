I simplified `latest_updates` in `inventory/feed.py`. It no longer walks the feed backwards and reverses the result twice. It now records the index of each SKU's last update and returns those updates in feed order:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    # The warehouse resends a SKU to fix a miscount, so the last update for each
    # SKU wins. Results keep the feed order of those winning updates.
    last_index = {update["sku"]: i for i, update in enumerate(updates)}
    return [updates[i] for i in sorted(last_index.values())]
```

The output is unchanged. Each SKU still gets its last update, and the results still come out in the order those last updates appear in the feed. I checked this against the old version on a mixed feed, and the three existing tests in `tests/test_feed.py` pass.

I added one comment, recording the rule the old loop shape carried: the later update for a SKU wins because the warehouse resends it to fix a miscount. The reason comes from the existing test comment. I did not change `total_units` or the module docstrings.

Two things to check:
- Nothing in the tests or the code says the output order is meaningful. I kept it because the old code returned that order, so changing it would be a behaviour change. If callers don't need it, the code could return dict values in a different order instead.
- `tests/test_feed.py` has no test for the output order. If you want that behaviour pinned, a test would need to say why it matters.
