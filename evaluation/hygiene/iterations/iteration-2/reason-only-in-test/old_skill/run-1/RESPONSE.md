I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update is stored under its SKU after removing any earlier entry for that SKU, so the last update per SKU wins and the result keeps the order of each SKU's last update. The old version walked the list backwards, deduplicated, then reversed twice.

I also expanded the docstring to say why the last update wins: the warehouse corrects a miscount by sending the SKU again later in the feed. That reason was previously only in the test comment.

The three existing tests pass. I also checked the new function against the old one on 2,000 random feeds and the outputs matched exactly, including order. `total_units` and the tests are unchanged.

The changes are uncommitted.
