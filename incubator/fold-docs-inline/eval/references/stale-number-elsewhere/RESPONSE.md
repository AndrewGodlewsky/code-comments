I've retired docs/order-sync.md. What happened to each claim on it:

- **`orders/sync.py` makes the nightly copy of orders into the store.** Dropped: the module docstring says exactly that.
- **`sync_orders()` reads one page at a time, and an empty page means there are no more orders.** Dropped: the loop and its `if not orders: return written` show it, and `get_page`'s docstring says an empty list comes back after the last page.
- **`ShopClient.get_page()` tries each request up to 5 times, 2 seconds apart, because of the shop API's nightly maintenance (OPS-19).** Split. The OPS-19 reason moved to a comment above the retry loop in `ShopClient.get_page` (orders/client.py). The 5 tries are right but needed no comment: `ATTEMPTS = 5` in orders/settings.py says it. The "2 seconds apart" did not move, because it's wrong: `get_page` waits `pause_after(attempt)`, and orders/backoff.py doubles the pause after each failure, so the waits are 2, 4, 8 and then 16 seconds. Only the first is 2 seconds. I left the code alone; if fixed 2-second spacing is what you want, tell me and I'll change it as a separate step.
- **`PAGE_SIZE` has to stay at 250 or below (HTTP 400 above that).** Moved to a comment above `PAGE_SIZE` in orders/client.py.
- **`OrderStore.upsert()` replaces a stored order with the same id.** Dropped: the method is one line that does exactly that, and the class docstring says the store is keyed by order id.

Nothing left on the page needed a document, so I deleted it. docs/deployment.md is untouched, no code changed, and I added no files.
