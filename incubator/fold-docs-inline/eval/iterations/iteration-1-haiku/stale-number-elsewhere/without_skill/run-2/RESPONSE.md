I moved the four points from docs/order-sync.md into the code next to what they describe, then deleted the page. Nothing on it needed a standalone document.

- orders/client.py, above PAGE_SIZE: the shop API returns HTTP 400 and no orders for a page size above 250, so the value must stay at 250 or below.
- orders/client.py, in get_page(): the retry reason (about one dropped request in a thousand during nightly maintenance, OPS-19) and a pointer to orders/backoff.py for the waits.
- orders/sync.py, in sync_orders(): an empty page means there are no more orders.
- orders/store.py, upsert(): a stored order with the same id is replaced.

One correction on the way: the page said retries happen "2 seconds apart". The code does not do that. backoff.py doubles the wait after each failed attempt, so the waits across 5 attempts are 2, 4, 8 and 16 seconds. I wrote the correct sequence into the comment on PAUSE_SECONDS in orders/settings.py.

docs/order-sync.md is deleted. No other file in the repository linked to it, and docs/deployment.md and README.md are unchanged. The test suite passes (4 tests, `python -m unittest discover -s tests -t .`).
