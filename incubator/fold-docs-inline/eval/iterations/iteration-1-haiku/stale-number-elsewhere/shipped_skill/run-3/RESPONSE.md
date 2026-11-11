I moved the four points from docs/order-sync.md into the code and deleted the page. Nothing else on it still needs a document. The tests pass (4 of 4).

What moved, and where:

- **Page size limit** (`orders/client.py`, above `PAGE_SIZE`): the shop API answers a page size above 250 with HTTP 400 and no orders, so the value must stay at or below 250.
- **Retries** (`orders/client.py`, inside `ShopClient.get_page`): the shop API drops about one request in a thousand during its nightly maintenance (OPS-19), so each request gets several attempts.
- **Upsert rule** (`orders/store.py`, `OrderStore.upsert` docstring): a stored order with the same id is replaced.
- **Paging stop condition**: already documented in the `ShopClient.get_page` docstring ("an empty list once every order has been read"), so I did not add a second copy.

Things you should know:

- **The old page was wrong about retry timing.** It said retries come "2 seconds apart". `orders/backoff.py` doubles the pause after each failure (`PAUSE_SECONDS * 2 ** (failures - 1)`), so the waits are 2, 4, 8 and 16 seconds, up to 30 seconds in total for one request. I did not write a comment about the doubling. The code shows it and the reason was not recorded anywhere I could find. If you want the reason beside the code, please tell me what it is.
- **No reason is recorded for the page size of 200.** The limit is 250, but nothing I read says why 200 was chosen. I left it unexplained.
- `docs/deployment.md` was not in scope and is unchanged. Its scheduling and log facts (02:15 UTC on `ops-cron`, log at `/var/log/shopsync.log`) appear nowhere in the code. Decide whether they belong in that page or in ops documentation.
- Nothing else in the repo linked to `docs/order-sync.md`, so deleting it broke no links.
- I did not use git, and I did not change any existing comment that was still accurate.
