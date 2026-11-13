I moved the facts from docs/order-sync.md into comments next to the code and deleted the page. Nothing else linked to it.

- `orders/client.py`: a comment on `PAGE_SIZE` says the shop API rejects a page size above 250 with HTTP 400 and returns no orders. It is 200 today.
- `orders/settings.py`: the comment on `ATTEMPTS` and `RETRY_DELAY_SECONDS` now says why requests are retried (the shop API drops about one in a thousand during nightly maintenance, OPS-19).
- `orders/store.py`: a comment in `upsert()` says an order with an already-stored id replaces the stored one.
- Already in the code, so not repeated: the empty page ending the read is in the `get_page()` docstring and the `sync_orders()` loop.

The page was wrong about one thing. It said `get_page()` tries each request 3 times, but `ATTEMPTS` in `orders/settings.py` is 5. I did not copy the "3" anywhere, so the setting is the only place the number lives. If 3 was the intended value, that is a separate change to `ATTEMPTS`, and I haven't made it.

I did not run the tests.
