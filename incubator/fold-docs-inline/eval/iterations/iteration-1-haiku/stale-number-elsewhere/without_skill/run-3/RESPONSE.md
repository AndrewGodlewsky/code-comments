I moved the content of docs/order-sync.md into the code it describes and deleted the page. Nothing on it needed a standalone document. No other file linked to it.

What moved, and where:

- orders/client.py, above PAGE_SIZE: the page size must stay at 250 or below, because the shop API answers a larger page size with HTTP 400 and no orders.
- orders/client.py, ShopClient.get_page(): retries up to ATTEMPTS times in total, and the OPS-19 reason for expecting dropped requests during nightly maintenance.
- orders/backoff.py, pause_after(): the pause doubles with each failure.
- orders/sync.py, sync_orders(): pages are read until an empty page, and only orders within ORDER_WINDOW_DAYS are written.
- orders/store.py, OrderStore.upsert(): replaces any stored order with the same order id.

One correction while moving it: the old page said failed requests are retried "2 seconds apart". The code does not do that. It waits 2, 4, 8 and then 16 seconds, since the pause doubles with each failure. The comment in orders/backoff.py now states the actual behaviour, so the stale figure is gone with the page.

Left alone: docs/deployment.md (the 02:15 UTC schedule and log path belong to deployment, not to the sync code) and README.md. Neither refers to order-sync.md.

Verification: python -m unittest discover -s tests -t . runs 4 tests, all passing. I only changed comments and docstrings, so the code behaviour is unchanged.
