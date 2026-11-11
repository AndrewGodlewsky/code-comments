I folded `docs/order-sync.md` into the code and deleted it. One claim on it disagrees with the code, and I need you to say which side is right.

**Fate list (page order)**
1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." Dropped. The `orders/sync.py` module docstring says it.
2. "`sync_orders()` reads the shop API one page at a time." Dropped. The `sync_orders` loop shows it.
3. "An empty page means there are no more orders to read." Dropped. The `ShopClient.get_page` docstring and the `sync_orders` loop (`if not orders: return`) say it.
4. "`ShopClient.get_page()` tries each request up to 5 times." Dropped. `ATTEMPTS = 5` in `orders/settings.py` says it, and `tests/test_client.py` checks it.
5. "...2 seconds apart." **Not migrated.** `orders/backoff.py` `pause_after` returns `PAUSE_SECONDS * 2 ** (failures - 1)`, so the waits are 2, 4, 8 and 16 seconds, not a flat 2. The test only checks the first pause. Which is right: should the code be a flat 2 seconds, or was the page just out of date? I changed no code.
6. "...because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." Moved to a comment above the retry loop in `ShopClient.get_page` (`orders/client.py`), keeping OPS-19. The comment gives no attempt count or spacing.
7. "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders." Moved to a comment above `PAGE_SIZE` in `orders/client.py`. The current value, 200, is within the limit.
8. "`OrderStore.upsert()` replaces any stored order that has the same order id." Dropped. The `OrderStore` docstring ("keyed by the shop's order id") and the dict assignment in `upsert` say it.

**Other files**
- No file links to `docs/order-sync.md`.
- Nothing else states the moved facts. `docs/deployment.md` covers only schedule and log location, and I left it alone.
- Gap: the 1-in-1000 drop rate and the 250 limit are facts about the shop API. I can't check them against this repository, so I took them from the page as written.

The page is deleted because no kept claim remained.
