I simplified `latest_updates` in `inventory/feed.py`. It now makes one forward pass: each update removes any earlier entry for its SKU and then inserts itself, so the dict keeps each SKU's latest update in order of that latest update. The old version scanned the feed backwards and then reversed the result twice to get the same output. Behaviour is unchanged, including the output order, which the original code produced but no test checks.

I added a two-line comment beside the loop. It records that the later update wins because the warehouse resends a SKU to correct a miscount (taken from the existing test comment), and that the pop moves the SKU to the end, which sets the output order. `total_units` and the docstrings are unchanged.

Checks:
- The three existing tests pass (`python -m unittest discover -s tests -t .`).
- On 20,000 random feeds, the new function returns exactly the same list as the old one, order included.
- The example `[A1:5, B2:3, A1:4]` still returns `[B2:3, A1:4]`.

I did not add a test for output order. If you want that order guaranteed, a test for it would be the next step.
