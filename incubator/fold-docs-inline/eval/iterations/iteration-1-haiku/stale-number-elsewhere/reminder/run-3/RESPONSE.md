I moved the code-specific facts from docs/order-sync.md into comments and deleted the page, since nothing on it still needs a document.

What I did:
- orders/client.py, above PAGE_SIZE: the shop API answers a page size above 250 with HTTP 400 and no orders, so the value must stay at 250 or below. The current value (200) is within that limit.
- orders/client.py, above the retry loop in get_page(): the shop API drops about one request in a thousand during its nightly maintenance (OPS-19), so each request gets up to ATTEMPTS tries.
- Deleted docs/order-sync.md. No other file in the repository refers to it. docs/deployment.md and README.md are unchanged.

What I left out because the code already shows it: the sync reads one page at a time and stops on an empty page, the 14-day window, the 5-attempt limit, and that upsert replaces an order with the same id.

Claim the code contradicts, not carried over: the page says get_page() retries "2 seconds apart". The code does not wait a fixed 2 seconds. orders/backoff.py doubles the pause after each failure (pause_after = PAUSE_SECONDS * 2 ** (failures - 1)), so with the current settings the waits between the five attempts are 2, 4, 8 and then 16 seconds. PAUSE_SECONDS in orders/settings.py is only the first wait. The new comment does not state a timing. If the 2-second figure was the intended behaviour, the code needs changing, which I did not do.

No code was changed beyond the two comments, and no files were created other than this RESPONSE.md.
