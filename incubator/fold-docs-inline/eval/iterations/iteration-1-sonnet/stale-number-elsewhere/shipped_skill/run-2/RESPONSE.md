I deleted `docs/order-sync.md` and moved the parts that belong next to the code into comments. I haven't run the tests, and I changed no code, only comments and the page.

Where each fact went:
- **Retries (OPS-19):** the comment on `ATTEMPTS` in `orders/settings.py` now says the shop API drops about one request in a thousand during nightly maintenance, so dropped requests are retried.
- **Page size limit:** a comment on `PAGE_SIZE` in `orders/client.py` says it must stay at 250 or below, because a larger size gets HTTP 400 and no orders.
- **Replace on same id:** `OrderStore.upsert()` in `orders/store.py` now has a one-line docstring saying it replaces any stored order with the same order id.
- **Empty page ends the loop:** a one-line comment in `sync_orders()` in `orders/sync.py` says an empty page means there are no more orders. `ShopClient.get_page()` already documents this.
- **Not carried over:** the opening line about `sync.py` doing the nightly copy, since the module docstring already says it.

The page said requests are retried "2 seconds apart", which is wrong. `orders/backoff.py` doubles the wait after each failure (2, 4, 8, 16 seconds), so I did not copy that claim into any comment.

Nothing else pointed at the page: the README doesn't link to it, and `docs/deployment.md` covers the schedule and log without referring to it. I left `docs/deployment.md` alone.
