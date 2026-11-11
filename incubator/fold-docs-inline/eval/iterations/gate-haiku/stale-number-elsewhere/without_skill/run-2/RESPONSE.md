I moved the contents of docs/order-sync.md into the code and deleted the page. Nothing on it still needs a document, and nothing else in the repo linked to it.

What moved, and where:
- The page-by-page read and the empty-page stop condition are now in the `sync_orders()` docstring in `orders/sync.py`.
- The 250 page-size limit (the shop API returns HTTP 400 above it) is a comment on `PAGE_SIZE` in `orders/client.py`. The constant stays at 200, which is within the limit.
- The retry rationale (about one dropped request in a thousand during nightly maintenance, OPS-19) is a comment on `ATTEMPTS` in `orders/settings.py`. `get_page()` now points there.
- The upsert behaviour (same order id replaces the stored order) is in the `OrderStore.upsert()` docstring in `orders/store.py`.

One thing you should know: the page said retries happen "up to 3 times", but `ATTEMPTS` in `orders/settings.py` is 5. The code is what runs, so I did not restate a number in the comments. The old page was wrong on this point and is now gone. If 3 was the intended value, the constant needs changing and a test added; I did not change it.

The tests pass (`python -m unittest discover -s tests -t .`, 4 tests). `docs/deployment.md` and `README.md` are unchanged.
