I retired `docs/order-sync.md`: its content now lives in comments next to the code, and I deleted the page. Nothing on it needed to stay a document. Nothing else linked to it, and I didn't run the tests.

Where each point went:
- **Empty page ends the read:** a comment in `sync_orders()` in `orders/sync.py`.
- **Why requests are retried (the shop API drops about 1 in 1000 requests during nightly maintenance, OPS-19):** a comment on `ATTEMPTS` in `orders/settings.py`.
- **Page size limit:** a comment on `PAGE_SIZE` in `orders/client.py`. The shop API answers a page size above 250 with HTTP 400 and no orders.
- **`upsert()` replaces an order with the same id:** a comment in `OrderStore.upsert()` in `orders/store.py`.

I did not copy two things from the page because the code disagrees with them:
- The page said `PAGE_SIZE` "has to stay at 250 or below", and the code sets 200. The limit is 250, so I kept that figure in the comment and left the value alone.
- The page said retries are "2 seconds apart". `orders/backoff.py` doubles the wait each time (2s, 4s, 8s, 16s), so I left that out. The retry count and wait already live in `settings.py` and `backoff.py`.

I couldn't check the HTTP 400 behaviour or the OPS-19 maintenance claim from the code. They are carried over from the old page as written.
