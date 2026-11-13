# Fate list for docs/order-sync.md

One line per claim, in page order.

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." **Dropped.** `orders/sync.py` module docstring already says "Nightly copy of shop orders into the warehouse store."
2. "`sync_orders()` reads the shop API one page at a time; an empty page means there are no more orders to read." **Dropped.** `orders/sync.py` `sync_orders`: loops on `client.get_page(page)`, increments `page`, and returns on `if not orders`. `ShopClient.get_page` docstring says it returns an empty list once every order has been read.
3. "`ShopClient.get_page()` tries each request up to 5 times" **Dropped.** `orders/settings.py` `ATTEMPTS = 5`; `orders/client.py` `get_page` loops `range(1, ATTEMPTS + 1)`.
4. "2 seconds apart" **Not migrated.** `orders/backoff.py` `pause_after` returns `PAUSE_SECONDS * 2 ** (failures - 1)`, with `PAUSE_SECONDS = 2` in `orders/settings.py`. The waits between the 5 attempts are 2, 4, 8 and 16 seconds, not 2 seconds apart. Only the wait after the first failure is 2 seconds. Quoted: "2 seconds apart". Question for you: should the doc or the code be right? I changed no code.
5. "because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." **Moved** to `orders/settings.py`, comment above `ATTEMPTS` (added beside the existing "Attempts per shop API request." comment, which is unchanged). Reason: an outside fact the retry count relies on. Ticket id kept.
6. "`PAGE_SIZE` has to stay at 250 or below" **Moved** to `orders/client.py`, comment above `PAGE_SIZE`. Current value `PAGE_SIZE = 200` satisfies it. The 250 limit is a shop API contract that this repo cannot check; see gaps.
7. "the shop API answers a larger page size with HTTP 400 and returns no orders." **Moved** to the same comment above `PAGE_SIZE`. This is an outside contract the code relies on; cannot be checked here; see gaps.
8. "`OrderStore.upsert()` replaces any stored order that has the same order id." **Dropped.** `orders/store.py` `upsert` assigns `self.rows[order["id"]] = dict(order)`, and the `OrderStore` docstring says "Orders keyed by the shop's order id."

Heading "# Order sync" is not a claim; no kept claims remain.

## Other files

- Moved facts stated elsewhere: none found. Searched for "OPS-19", "250", "HTTP 400", "one in a thousand" and "2 seconds" across the repo; only `docs/order-sync.md` and the code named above matched.
- Links to the page or removed sections: none. `README.md` and `docs/deployment.md` do not link to `order-sync.md`.

## Gaps and outcome

- Not verifiable here: the shop API's 250-row page-size limit, its HTTP 400 response, and the "one request in a thousand" failure rate (OPS-19). Those comments record the page's claims as written, and the owner should confirm them against the shop API or the ticket.
- Unresolved conflict: the "2 seconds apart" claim (item 4). Decide whether the retry wait should be fixed at 2 seconds (code change in `orders/backoff.py`) or the doc's wording should stand as an accepted deviation. Nothing was changed for it.
- `docs/order-sync.md` was deleted: after the moves and drops, no kept claims remained. The one unresolved claim is listed above, not kept in a document.
- Files changed: `orders/settings.py` (comment added), `orders/client.py` (comment added), `docs/order-sync.md` (deleted). No other files changed.
