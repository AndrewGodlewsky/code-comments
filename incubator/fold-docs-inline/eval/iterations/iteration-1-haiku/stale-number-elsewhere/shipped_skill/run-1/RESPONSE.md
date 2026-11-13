I moved the parts of docs/order-sync.md that describe the code into comments beside that code, then deleted the page. Nothing on it needed a separate document: the rest of it was code description, and README.md and docs/deployment.md cover the overview and schedule.

Changes:
- orders/client.py, above `PAGE_SIZE`: the shop API answers a larger page size with HTTP 400 and no orders, so the value must stay at or below 250.
- orders/client.py, `ShopClient.get_page` docstring: the shop API drops about one request in a thousand during nightly maintenance (OPS-19), so dropped requests are retried up to `ATTEMPTS` times, with a longer wait after each failure.
- orders/sync.py, at the empty-page check: an empty page means the shop has no more orders.
- docs/order-sync.md: deleted. Nothing else in the repository links to it.

One correction: the old page said failed requests are retried "2 seconds apart". That was false. `pause_after` in orders/backoff.py doubles the wait after each failure, so the page was wrong about the spacing. The new comment says the wait grows and points to `pause_after` rather than copying the values, so it cannot go stale when the settings change.

Not recorded: the page's statement that `OrderStore.upsert()` replaces an order with the same id. The code shows this directly, so I left it out.

Tests: `python -m unittest discover -s tests -t .` passes, 4 of 4. Only comments and the deleted page changed. I removed the `__pycache__` folders the run created.
