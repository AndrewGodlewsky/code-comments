I folded docs/order-sync.md into the code and deleted it, since none of its claims needed a document. Fate list, in page order:

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." Dropped. The module docstring of `orders/sync.py` already says this.
2. "`sync_orders()` reads the shop API one page at a time; an empty page means there are no more orders to read." Dropped. `sync_orders` in `orders/sync.py` loops with `page += 1` and returns on `if not orders`; the `get_page` docstring in `orders/client.py` states the empty-list end condition.
3. "`ShopClient.get_page()` tries each request up to 5 times" Dropped. `ATTEMPTS = 5` in `orders/settings.py`, used by the loop in `ShopClient.get_page`; `test_gives_up_after_the_last_attempt` checks it.
4. "2 seconds apart" Not migrated. `pause_after` in `orders/backoff.py` returns `PAUSE_SECONDS * 2 ** (failures - 1)`, so the waits are 2, 4, 8 and 16 seconds between the five attempts, not a flat 2 seconds. `PAUSE_SECONDS` in `orders/settings.py` is documented as the wait after the first failed attempt. No comment written; the user must decide which side is right.
5. "because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." Moved. Comment added above the retry loop in `ShopClient.get_page`, `orders/client.py`, with the ticket id kept.
6. "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders." Moved. Comment added above `PAGE_SIZE` in `orders/client.py`. The current value of 200 satisfies it, so nothing conflicts.
7. "`OrderStore.upsert()` replaces any stored order that has the same order id." Dropped. `upsert` in `orders/store.py` does `self.rows[order["id"]] = dict(order)`, which shows the replacement.

Nothing was kept, so `docs/order-sync.md` is deleted. The not-migrated claim (item 4) went with it; its text is quoted above.

Follow-ups:
- Gaps for you to fill: the one-in-a-thousand drop rate and OPS-19 are shop API facts I could not check against this repository. The 250-page-size limit is also an external fact I could not check here.
- Other files stating moved facts: none found by search of the repository.
- Files linking to the page: none. `README.md` and `docs/deployment.md` do not link to `order-sync.md`.
- No code was changed. The only edits are the two comments in `orders/client.py`.
