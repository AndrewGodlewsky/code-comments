I simplified `latest_updates` in `inventory/feed.py`. The old version walked the feed backwards, collected the first sighting of each SKU, then reversed the result twice to restore order. The new version makes one forward pass: it removes and re-inserts each SKU's entry, so the dict holds each SKU's latest update in order of that last update.

The output is unchanged. The three existing tests pass, and I checked the old and new versions against each other on 5,000 random feeds, including the order of the results.

One thing needs your input. The result order is the position of each SKU's last update in the feed. Nothing in the tests or docstring says that order is required, and I found no reason for it in the repo. I kept it and added a comment explaining the pop-and-reinsert trick. If callers do not depend on the order, the code can be simplified further, for example to a plain dict comprehension. Can you tell me whether the order matters, and why?
