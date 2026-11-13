# Fate list for docs/order-sync.md

Deleted `docs/order-sync.md`. No kept claim remained, so the page is gone.

| Claim (page order) | Fate | Evidence |
|---|---|---|
| `orders/sync.py` makes the nightly copy of shop orders into the warehouse store. | Dropped | `orders/sync.py` line 1 module docstring states it. |
| `sync_orders()` reads the shop API one page at a time. | Dropped | `orders/sync.py` `sync_orders`: loop with `page += 1` and `client.get_page(page)`. |
| An empty page means there are no more orders to read. | Dropped | `orders/sync.py` `if not orders: return written`; `ShopClient.get_page` docstring. |
| `ShopClient.get_page()` tries each request up to 5 times. | Dropped | `orders/settings.py` `ATTEMPTS = 5`; `get_page` loops over `ATTEMPTS`; `tests/test_client.py` `test_gives_up_after_the_last_attempt`. |
| "2 seconds apart" between attempts. | Not migrated | `orders/backoff.py` `pause_after` returns `PAUSE_SECONDS * 2 ** (failures - 1)`, with `PAUSE_SECONDS = 2` in `orders/settings.py`. Waits are 2, 4, 8, 16 seconds (exponential), not a fixed 2 seconds. Only the first pause is 2 seconds. Removed from the page, not written into any comment. |
| Retries exist because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19). | Moved | `orders/client.py` `ShopClient.get_page`, comment above the retry loop, with the ticket id. |
| `PAGE_SIZE` has to stay at 250 or below; the shop API answers a larger page size with HTTP 400 and returns no orders. | Moved | `orders/client.py` `PAGE_SIZE`, comment above the constant. Current value 200 satisfies the limit, so no conflict. |
| `OrderStore.upsert()` replaces any stored order that has the same order id. | Dropped | `orders/store.py` `upsert` assigns `self.rows[order["id"]]`; class docstring "Orders keyed by the shop's order id." |

## Files changed
- `docs/order-sync.md`: deleted.
- `orders/client.py`: two comments added (above `PAGE_SIZE` and above the retry loop in `get_page`). No code changed.
- Test run after the edits: 4 tests, OK. Bytecode caches from the run were removed.

## Other files
- No other file in this repository states the moved facts, so there is nothing to reconcile.
- No file links to `docs/order-sync.md` (checked `README.md` and `docs/deployment.md`).

## For you to decide
- The page's "2 seconds apart" does not match the code, which backs off exponentially (2, 4, 8, 16 seconds). Decide which is right. If the code is right, nothing needs writing. If the fixed 2-second gap is what you want, `orders/backoff.py` needs changing. Either way the claim is no longer in the repo, so the decision lives only in this list.
- Gap: the shop API facts (one dropped request in a thousand, the 250 page-size limit, HTTP 400 behavior) come from the page and are not checked here. They are moved as written and cannot be verified from this repository.
