I moved the contents of `docs/order-sync.md` into comments next to the code and deleted the page. Nothing else on it needed a document, and no other file linked to it.

Where each fact went:
- **`orders/client.py`:** the rule that `PAGE_SIZE` must stay at 250 or below, because the shop API answers a larger page size with HTTP 400 and returns no orders.
- **`orders/settings.py`:** the reason for retrying (the shop API drops about one request in a thousand during nightly maintenance, OPS-19), next to `ATTEMPTS`.
- **`orders/sync.py`:** an empty page means there are no more orders to read.
- **`orders/store.py`:** `upsert()` replaces any stored order with the same id.

The page said requests are retried "2 seconds apart", which is out of date. `orders/backoff.py` doubles the wait after each failure, starting from `PAUSE_SECONDS` (2). I did not copy the "2 seconds apart" claim. The `PAUSE_SECONDS` comment now points to `backoff.py` for how later waits grow.

I did not copy the "5 times" figure either, since `ATTEMPTS` in `settings.py` already holds it.

I did not run the tests, but I only added comments.
