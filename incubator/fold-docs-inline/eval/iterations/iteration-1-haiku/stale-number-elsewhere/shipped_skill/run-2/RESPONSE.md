I moved everything in docs/order-sync.md into comments next to the code and deleted the page. Nothing else in the repo linked to it, and the unit tests pass (4 of 4).

Where each point went:
- The empty-page end-of-orders rule is now a comment above the `if not orders:` check in `orders/sync.py`.
- The retry rule and the OPS-19 reason are now a comment above the retry loop in `ShopClient.get_page()` in `orders/client.py`.
- The 250-or-below page size limit (HTTP 400 above it) is now a comment above `PAGE_SIZE` in `orders/client.py`.
- The replace-on-same-id behaviour is now a docstring on `OrderStore.upsert()` in `orders/store.py`.

One correction: the old page said failed requests are retried "2 seconds apart". The code does not do that. `pause_after()` in `orders/backoff.py` doubles the pause after each failure, starting at `PAUSE_SECONDS` (2), so the waits are 2, 4, 8 and 16 seconds. The new comment describes the doubling, and I did not carry the "2 seconds apart" wording over.

Gaps to check:
- OPS-19 is copied from the old page. I could not verify it, and I did not check that it is the right tracker id.
- The "one request in a thousand" figure comes from the old page. I could not verify it either.
- `docs/deployment.md` still covers the 02:15 UTC schedule and the log path. I left it alone because it is not part of this retirement.
