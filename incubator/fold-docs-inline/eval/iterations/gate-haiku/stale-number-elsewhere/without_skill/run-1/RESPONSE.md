I moved the content of docs/order-sync.md into comments and docstrings next to the code it describes, then deleted the page. Nothing on it needed a standalone document.

- orders/settings.py: the retry rationale (the shop API drops about one request in a thousand during nightly maintenance, OPS-19) now sits above ATTEMPTS and RETRY_DELAY_SECONDS.
- orders/client.py: the rule that PAGE_SIZE must stay at 250 or below (the shop API returns HTTP 400 and no orders above that) now sits above PAGE_SIZE.
- orders/sync.py: the sync_orders() docstring now says it reads one page at a time and that an empty page means there are no more orders.
- orders/store.py: the upsert() docstring now says it replaces any stored order with the same order id.

The old page said requests were tried 3 times, 2 seconds apart. The code and tests use ATTEMPTS = 5, so I did not carry the 3 over. The comment points at the setting, not a copy of the number.

docs/deployment.md does not link to the deleted page and is unchanged. The README does not reference it either. I left the deployment page alone because it is not part of this retirement.

The unit tests pass (4 tests, python -m unittest discover -s tests -t .).
