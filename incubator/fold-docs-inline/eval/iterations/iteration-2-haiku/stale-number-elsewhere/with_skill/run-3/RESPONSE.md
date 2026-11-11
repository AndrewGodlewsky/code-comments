I moved the two facts that belong beside the code into comments and deleted `docs/order-sync.md`, because no kept claim remained. One claim conflicts with the code and needs your decision. Only comments changed; the tests still pass.

**Fate list** (page order)

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." Dropped. `orders/sync.py` line 1 (module docstring) states it.
2. "`sync_orders()` reads the shop API one page at a time" Dropped. `orders/sync.py` loop increments `page` per iteration.
3. "an empty page means there are no more orders to read." Dropped. `orders/sync.py`: `if not orders: return written`.
4. "`ShopClient.get_page()` tries each request up to 5 times" Dropped. `orders/settings.py` `ATTEMPTS = 5` ("Attempts per shop API request."); `orders/client.py` loops `range(1, ATTEMPTS + 1)`.
5. "2 seconds apart" Not migrated. `orders/backoff.py` `pause_after()` returns `PAUSE_SECONDS * 2 ** (failures - 1)`. With `PAUSE_SECONDS = 2` (`orders/settings.py`), the waits between the 5 attempts are 2, 4, 8 and 16 seconds, not a fixed 2 seconds. Which is right is your call: keep the exponential backoff and correct the claim, or change the code to a fixed 2-second pause.
6. "because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." Moved to `orders/client.py`, `ShopClient.get_page`, as a comment above the retry loop. The ticket id is kept.
7. "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders." Moved to `orders/client.py`, `PAGE_SIZE`, as a comment above the constant. The current value, 200, is within the limit.
8. "`OrderStore.upsert()` replaces any stored order that has the same order id." Dropped. `orders/store.py` `upsert` assigns `self.rows[order["id"]]`, and the class docstring says "Orders keyed by the shop's order id."

The heading "# Order sync" is not a claim.

**Other files**
- No other file states the moved facts (checked `OPS-19`, `250`, `PAGE_SIZE`, retry and upsert wording).
- No file links to `docs/order-sync.md`. `README.md` and `docs/deployment.md` do not link to it.

**Gaps for you to fill**
- The one-in-a-thousand drop rate, OPS-19 and the 250 page-size limit describe the shop API, which is outside this repository. They are moved as written and could not be checked here.
- Item 5 is unresolved. The "2 seconds apart" wording is removed from the repo, so its only record is this reply. Recover the original page from version history if you need the exact text.
- `docs/order-sync.md` is deleted. `docs/deployment.md` is untouched.
