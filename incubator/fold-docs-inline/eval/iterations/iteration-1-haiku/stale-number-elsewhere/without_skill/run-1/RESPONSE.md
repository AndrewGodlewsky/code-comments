I moved the content of docs/order-sync.md into comments next to the code it describes and deleted the page. Nothing on it needed a standalone document.

What moved where:

- `orders/sync.py`: a comment on the empty-page check. An empty page means there are no more orders.
- `orders/client.py`: a comment on `PAGE_SIZE` that the shop API answers any larger page size with HTTP 400 and no orders, so it must stay at 250 or below. The retry rationale (about 1 in 1000 requests dropped during nightly maintenance, OPS-19) is in the `get_page()` docstring.
- `orders/settings.py`: the same OPS-19 rationale on `ATTEMPTS`, and the pause behaviour on `PAUSE_SECONDS`.
- `orders/store.py`: the `upsert()` docstring says it replaces any stored order with the same id.

One correction: the old page said retries happen "2 seconds apart". The code does not do that. `backoff.pause_after` doubles the wait after each failure, so with 5 attempts the pauses are 2, 4, 8 and 16 seconds. The new comments describe the code as it is.

`docs/deployment.md` is unchanged. It already holds the 02:15 UTC schedule and the log path, which are operational facts rather than code facts. Nothing else in the repo referred to `order-sync.md`.

Tests: `python -m unittest discover -s tests -t .` runs 4 tests, all passing. No code behaviour changed, only comments and one docstring.
