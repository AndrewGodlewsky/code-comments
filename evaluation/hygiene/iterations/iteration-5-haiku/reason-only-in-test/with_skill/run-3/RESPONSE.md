I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass that keeps the last update for each SKU, instead of walking the feed backwards and reversing the result twice. Output is unchanged: each SKU appears once with its last update, in the order those last updates occur in the feed. The existing tests pass (3 of 3), and I checked a mixed sample feed by hand against the old code.

I also added a short comment stating that a later update replaces an earlier one, and why (the warehouse resends a SKU to correct a miscount). The `test_later_update_wins` test already explains this, so the comment repeats only the rule and its reason.

Changes are uncommitted. No git or GitHub commands were run.
