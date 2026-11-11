I moved the code-specific facts from docs/order-sync.md into comments and deleted the page, since nothing left on it needs a document.

What changed:
- orders/client.py: added a comment above PAGE_SIZE saying the shop API answers a page size above 250 with HTTP 400 and no orders, so keep it at 250 or below. The current value of 200 is within that limit.
- orders/client.py: added a comment in get_page() saying the shop API drops about one request in a thousand during nightly maintenance (OPS-19), which is why each request gets up to ATTEMPTS tries.
- docs/order-sync.md: deleted. No other file in the repository referred to it.

Left off the page because the code already shows it: sync.py reads pages until one comes back empty, sync_orders() copies the nightly orders, and OrderStore.upsert() replaces an order with the same id.

Contradicted by the code, so not carried over:
- The page says get_page() retries "2 seconds apart". The code does not do that. orders/backoff.py doubles the pause after each failure, using PAUSE_SECONDS = 2 as the base, so the waits are 2, 4, 8 and then 16 seconds across the 5 attempts. Only the first wait is 2 seconds. The test in tests/test_client.py checks only the first pause, which is consistent with the code.

No code was changed beyond the two comments, and no files were created other than this RESPONSE.md. I did not touch docs/deployment.md or README.md.
