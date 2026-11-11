I moved the two facts that belong beside the code into comments in `orders/client.py` and deleted `docs/order-sync.md`. Nothing else changed. One line on the page contradicts the code, so I left it out. It's the second item in the list below.

Fate list, in page order:
- "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store": dropped. The `orders/sync.py` module docstring says this.
- "`sync_orders()` reads the shop API one page at a time; an empty page means no more orders": dropped. The `sync_orders` loop and the `ShopClient.get_page` docstring state it.
- "`get_page()` tries each request up to 5 times": dropped. `ATTEMPTS = 5` in `orders/settings.py`, and `tests/test_client.py` checks it.
- "...2 seconds apart": **not migrated**. The wait is not a constant 2 seconds. `orders/backoff.py` `pause_after()` returns `PAUSE_SECONDS * 2 ** (failures - 1)`, with `PAUSE_SECONDS = 2`. The waits are 2, 4, 8 and 16 seconds. Which is right, the page or the code? I changed no code.
- "...because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)": moved to a comment above the retry loop in `ShopClient.get_page` (`orders/client.py`), keeping OPS-19.
- "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders": moved to a comment above `PAGE_SIZE` in `orders/client.py`. The current value is 200, which is within the limit.
- "`OrderStore.upsert()` replaces any stored order that has the same order id": dropped. The name `upsert`, the `OrderStore` docstring ("keyed by the shop's order id") and `rows[order["id"]] = ...` in `orders/store.py` say it.

Follow-ups:
- No file links to `docs/order-sync.md`, and no other file states the moved facts. `README.md` and `docs/deployment.md` are unchanged.
- Gaps: the 1-in-1000 drop rate and the 250 page-size limit are facts about the shop API. Nothing in this repository checks them.
- The page is deleted. Every claim on it was dropped, moved or not migrated, and none was kept.
