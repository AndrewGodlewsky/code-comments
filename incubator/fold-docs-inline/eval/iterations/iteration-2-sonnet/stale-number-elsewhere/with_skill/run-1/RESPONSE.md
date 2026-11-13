I folded docs/order-sync.md into comments and deleted it. Fate list, in page order:

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store" - dropped. The module docstring in orders/sync.py says it.
2. "`sync_orders()` reads the shop API one page at a time" - dropped. The page loop in `sync_orders` shows it.
3. "an empty page means there are no more orders to read" - dropped. `sync_orders` returns on an empty page, and the `ShopClient.get_page` docstring says it.
4. "`get_page()` tries each request up to 5 times" - dropped. `ATTEMPTS = 5` in orders/settings.py, used by the loop in `get_page`.
5. "2 seconds apart" - not migrated. `pause_after` in orders/backoff.py doubles the wait: 2, 4, 8 then 16 seconds (`PAUSE_SECONDS * 2 ** (failures - 1)`), so the attempts are not evenly spaced. Which side is right, the page or the code?
6. "because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)" - moved. It is now a comment above the retry loop in `ShopClient.get_page` (orders/client.py). It is an outside fact the code relies on, so I kept it as the page wrote it.
7. "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders" - moved. It is now a comment above `PAGE_SIZE` in orders/client.py. The code's value is 200, which is within the limit.
8. "`OrderStore.upsert()` replaces any stored order that has the same order id" - dropped. `upsert` assigns `rows[order["id"]]`, and the class docstring says orders are keyed by id.

Other files stating a moved fact: none. README.md and docs/deployment.md do not mention the retry reason or the page-size limit.
Links to the page: none. Nothing links to docs/order-sync.md.
Gaps: none. docs/order-sync.md is deleted because no kept claim remained. Only the "2 seconds apart" decision is open. No code was changed.
