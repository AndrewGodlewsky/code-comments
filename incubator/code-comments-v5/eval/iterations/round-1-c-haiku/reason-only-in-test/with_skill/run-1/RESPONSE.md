I simplified `latest_updates` in `inventory/feed.py`. The old version walked the feed backwards, kept the first SKU it saw, and reversed the result twice. The new version walks the feed forwards and lets each later update replace the earlier one:

```python
latest = {}
for update in updates:
    latest.pop(update["sku"], None)
    latest[update["sku"]] = update
return list(latest.values())
```

Behaviour is unchanged. The result still has one entry per SKU, the last update for each SKU wins, and entries stay in the order of each SKU's last update in the feed. I checked this against the original logic on 20,000 random feeds, and all three existing tests pass. I left the tests unchanged.

I added a comment beside the loop that records the later-wins rule and its reason, which comes from `test_later_update_wins`: the warehouse resends a SKU to fix a miscount. It also explains that the `pop` is what keeps each SKU at the position of its last update.

One gap for you to settle: nothing in the repo says why the output is ordered by each SKU's last update. I kept that order because the current code produces it and no test depends on a different one. If the order matters to a caller, please tell me the reason so I can record it. If it does not matter, `{u["sku"]: u for u in updates}` would be shorter, but it orders by each SKU's first appearance instead, so it is a behaviour change and I did not make it.
