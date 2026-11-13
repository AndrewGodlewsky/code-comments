I deleted docs/order-sync.md. Nothing on it needed a document, and no other file linked to it.

Moved into comments:
- orders/settings.py, above `ATTEMPTS`: the shop API drops about one request in a thousand during its nightly maintenance (OPS-19), which is why requests are retried. The 5 attempts match the code.
- orders/client.py, above `PAGE_SIZE`: the shop API answers a page size above 250 with HTTP 400 and returns no orders. The current value of 200 is within that limit.

Left out because the code already shows it:
- An empty page means there are no more orders (the `get_page` docstring and the loop in `sync_orders`).
- `upsert()` replaces a stored order with the same id (it assigns by `order["id"]` in a dict).

Contradicted by the code, so I did not carry it over:
- The page said retries are "2 seconds apart". `orders/backoff.py` doubles the wait each time, so the pauses are 2, 4, 8 and 16 seconds. Only the first pause is `PAUSE_SECONDS` (2).

I changed no code and created no new files. I did not run the tests.
