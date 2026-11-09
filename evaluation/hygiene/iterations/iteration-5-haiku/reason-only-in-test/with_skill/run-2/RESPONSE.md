I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update is removed and re-inserted under its SKU, so a SKU's entry sits at the position of its last update. The old version walked the feed backwards and reversed the result twice. I left the output unchanged, including order. I checked the new version against the old one on 20,000 random feeds and they matched exactly, and the three existing tests pass.

I also expanded the docstring to state the rule the old shape hid: the last update for a SKU wins, because the warehouse corrects a miscount by sending the SKU again further down the feed. That reason comes from the existing test comment. Nothing else in the file changed, and I did not touch the tests.

Open question: I could not find a reason for the output order (ordered by each SKU's last update). Nothing I read says whether callers depend on it. If order does not matter, `{u["sku"]: u for u in updates}.values()` would be simpler still, but it would order by first appearance instead, so I kept the current order. If you can tell me the reason for the order, I will add it beside the code.

Nothing has been committed.
