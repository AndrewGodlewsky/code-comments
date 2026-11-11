I moved the code-specific facts from docs/order-sync.md into comments and deleted the page, since nothing on it still needs a document.

Moved into comments:
- orders/settings.py, beside ATTEMPTS: the shop API drops about one request in a thousand during its nightly maintenance (OPS-19).
- orders/client.py, beside PAGE_SIZE: the shop API answers a page size above 250 with HTTP 400 and no orders, so PAGE_SIZE has to stay at 250 or below.

Left out because the code already shows it:
- orders/sync.py is the nightly copy; sync_orders() reads one page at a time and stops on an empty page.
- OrderStore.upsert() replaces a stored order with the same id.
- ShopClient.get_page() makes up to ATTEMPTS (5) attempts.

Contradicted by the code, not carried over:
- The page says ShopClient.get_page() retries "2 seconds apart". The code does not do that. orders/backoff.py doubles the wait after each failure, so the pauses are 2, 4, 8 and then 16 seconds. PAUSE_SECONDS = 2 is only the first pause. Someone should decide whether the page or the code is the intended behaviour; I left the code alone as asked.

Other changes:
- Deleted docs/order-sync.md. No other file in the repo referenced it.
- No code was changed beyond the two comments, and no new files were created other than this RESPONSE.md.
- docs/deployment.md and README.md are untouched.
