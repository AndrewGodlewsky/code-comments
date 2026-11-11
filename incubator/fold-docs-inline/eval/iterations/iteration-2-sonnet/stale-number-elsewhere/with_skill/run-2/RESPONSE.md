I folded `docs/order-sync.md` into `orders/client.py` and deleted the page. Nothing on it still needed a document. One claim on the page is wrong, so please decide which side is right.

Fate list, in page order:

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." Dropped. The `orders/sync.py` module docstring says this.
2. "`sync_orders()` reads the shop API one page at a time." Dropped. The page loop in `sync_orders` shows it.
3. "An empty page means there are no more orders to read." Dropped. `sync_orders` returns on an empty page, and the `ShopClient.get_page` docstring says it.
4. "`ShopClient.get_page()` tries each request up to 5 times." Dropped. `ATTEMPTS = 5` in `orders/settings.py` and the retry loop in `get_page` show it, and `tests/test_client.py` covers it.
5. "...2 seconds apart." Not migrated. The code waits `pause_after(attempt)`, which is `PAUSE_SECONDS * 2 ** (failures - 1)`. With `PAUSE_SECONDS = 2` the waits are 2, 4, 8 and 16 seconds, so the gaps grow. Which side is right? The code is exponential backoff and the page says fixed 2 seconds.
6. "...because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." Moved. It is now a comment above the retry loop in `ShopClient.get_page` in `orders/client.py`.
7. "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders." Moved. It is now a comment above `PAGE_SIZE` in `orders/client.py`. The current value of 200 is within the limit.
8. "`OrderStore.upsert()` replaces any stored order that has the same order id." Dropped. `upsert` writes `rows[order["id"]]`, and the `OrderStore` docstring says the rows are keyed by order id.

Other places that state a moved fact: none.

Links to the deleted page: none found in the repo.

Gaps: none. `docs/deployment.md` and `README.md` were not touched.

The page is deleted.
