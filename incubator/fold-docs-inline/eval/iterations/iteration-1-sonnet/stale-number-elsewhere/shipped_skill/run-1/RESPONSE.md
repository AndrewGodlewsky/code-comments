I moved the facts from `docs/order-sync.md` into comments next to the code and deleted the page. Nothing else linked to it, and I didn't run the tests.

- **Retries:** `orders/settings.py` now says why `ATTEMPTS` exists: the shop API drops about one request in a thousand during nightly maintenance (OPS-19).
- **Page size:** `orders/client.py` now says `PAGE_SIZE` must not exceed 250, because the shop API answers a larger page with HTTP 400 and returns no orders.
- **Upsert:** `OrderStore.upsert()` in `orders/store.py` now has a docstring saying it replaces any stored order with the same id.
- **End of orders:** the empty-page rule was already in the `get_page()` docstring, so I left it as it was.
- **Wrong retry timing:** the page said retries are "2 seconds apart", but `orders/backoff.py` doubles the wait each time (2, 4, 8, 16 seconds). I didn't copy the claim, and the existing comments in `orders/settings.py` and `orders/backoff.py` already describe the real behaviour.
- **Attempt count and wait:** I didn't repeat "5 attempts" or "2 seconds" in prose, since they live in `ATTEMPTS` and `PAUSE_SECONDS`.
