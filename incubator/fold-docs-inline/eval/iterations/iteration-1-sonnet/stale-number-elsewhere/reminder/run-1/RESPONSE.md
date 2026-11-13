I moved two facts into code comments and deleted docs/order-sync.md, since nothing on it still needed a document. I didn't run the tests.

**Moved into comments**
- `orders/settings.py`, on `ATTEMPTS`: the shop API drops about one request in a thousand during its nightly maintenance (OPS-19). That is the reason for retrying, and the code doesn't show it.
- `orders/client.py`, on `PAGE_SIZE`: the shop API answers a page size above 250 with HTTP 400 and returns no orders. The current 200 is under that limit, but nothing in the code says why it shouldn't go higher.

**Left out because the code already shows it**
- An empty page means there are no more orders. `sync_orders()` stops on an empty page, and the `get_page()` docstring says so.
- `OrderStore.upsert()` replaces an order with the same id. It writes `rows[order["id"]]`, and the store's docstring says orders are keyed by id.
- "Up to 5 times" is `ATTEMPTS = 5` in `settings.py`.

**Not carried over because the code contradicts it**
- The page said retries are "2 seconds apart". They aren't. `orders/backoff.py` doubles the wait after each failure: `PAUSE_SECONDS * 2 ** (failures - 1)`. With `PAUSE_SECONDS = 2` the waits are 2, 4, 8 and 16 seconds. Only the first wait is 2 seconds. The page should not have said otherwise, and I did not write a retry-spacing comment.

**Deleted**
- `docs/order-sync.md` is gone. Nothing else referenced it. `README.md` and `docs/deployment.md` are unchanged, and `docs/deployment.md` still holds the schedule and log location.

No code changed and no new files were created beyond this message.
