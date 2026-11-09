I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass and keeps the last update for each SKU, replacing the reversed walk and the double reversal:

```python
def latest_updates(updates):
    """Return the update to apply for each SKU."""
    latest = {}
    for update in updates:
        # Re-inserting moves the SKU to the end, so order follows each SKU's last update.
        latest.pop(update["sku"], None)
        latest[update["sku"]] = update
    return list(latest.values())
```

The output is unchanged, including order. Results are still ordered by each SKU's last update, which is what the old version returned. The existing tests pass (3 of 3). I also checked a mixed case by hand against the old logic, and the output matched.

I did not touch `total_units` or the tests.
