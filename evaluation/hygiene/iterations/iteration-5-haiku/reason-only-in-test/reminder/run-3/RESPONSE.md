I simplified `latest_updates` in `inventory/feed.py`. It no longer walks the list backwards, reverses it twice, and tracks a `seen` dict. It now makes one forward pass into a dict. For each update it pops the SKU's key and re-inserts it, so the key moves to the end and the dict's order follows each SKU's latest update. The function returns `list(latest.values())`.

The output order is the same as before. I checked this by hand on `A1, B2, C3, A4, C5`, which gives `B2, A4, C5` both before and after the change. The existing docstrings are still accurate, so I left them alone. I added one short comment on the pop/re-insert line, because the ordering behaviour is not obvious from the code.

The three existing tests in `tests/test_feed.py` pass (`python -m unittest discover -s tests -t . -v`). Nothing was committed, and I did not use git.
