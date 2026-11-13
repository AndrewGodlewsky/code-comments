I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update replaces the SKU's earlier entry, and the result is the list of those entries. The old version walked the feed backwards and then reversed the result twice.

The output is unchanged, including order. Results stay in the order of each SKU's last update in the feed, which the old reversal produced without saying so. I kept that order on purpose and noted it in a comment, because a plain dict comprehension would order results by first appearance instead.

I added a comment stating the rule that later updates win and the warehouse reason for it, which the old shape implied and the test comment explains. I did not change the tests.

Verification: the three unit tests pass. I also compared the old and new functions on 20,000 random feeds, and they matched exactly.

Question for you: does any caller depend on the output order? If not, the ordering comment and the `pop` line could be dropped and the code reduced to a dict comprehension.
