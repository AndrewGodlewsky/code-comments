I folded docs/order-sync.md into the code and deleted the page, since no claim on it needed a document. Tests pass (4 of 4).

Fate list, in page order:

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." Dropped. orders/sync.py:1 module docstring already says it.
2. "`sync_orders()` reads the shop API one page at a time." Dropped. orders/sync.py:13-21 loops over client.get_page(page) and increments page.
3. "an empty page means there are no more orders to read." Dropped. orders/sync.py:15-16 returns on an empty page; orders/client.py get_page docstring states it.
4. "`ShopClient.get_page()` tries each request up to 5 times." Dropped. orders/settings.py:6-7 sets ATTEMPTS = 5 with its comment; orders/client.py:18 loops over ATTEMPTS.
5. "2 seconds apart." Not migrated. orders/backoff.py:6-8 pause_after() returns PAUSE_SECONDS * 2 ** (failures - 1), so waits are 2, 4, 8, 16 seconds for failures 1 to 4 (orders/settings.py:9 documents PAUSE_SECONDS as the wait after the first failure). Left out of every comment. Which is right: fixed 2-second pauses, or doubling backoff?
6. "because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." Moved to orders/client.py, ShopClient.get_page, a comment above the retry loop. Ticket OPS-19 kept.
7. "`PAGE_SIZE` has to stay at 250 or below." Moved to orders/client.py, comment above PAGE_SIZE. The 250 limit is a shop API contract; PAGE_SIZE is 200 in the code, which satisfies it.
8. "the shop API answers a larger page size with HTTP 400 and returns no orders." Moved to the same comment above PAGE_SIZE.
9. "`OrderStore.upsert()` replaces any stored order that has the same order id." Dropped. orders/store.py:5 class docstring says orders are keyed by order id; orders/store.py:11 assigns self.rows[order["id"]], which replaces.

Gaps for you to check:
- The shop API behaviour in claims 6 to 8 (one dropped request in a thousand during nightly maintenance, HTTP 400 above 250) comes from outside this repo. Nothing here tests it, so I could not verify it.
- The page's 2-second pacing claim (claim 5) conflicts with the code. The code is the source for the comments, so no comment states the 2-second figure. Please decide which side is right, then fix either the code or the comment.

Other files: no other file in this repo states the moved facts, and none links to docs/order-sync.md or to a removed section. docs/deployment.md covers the cron schedule only.

Changed files: orders/client.py (two comments added, no code changed), docs/order-sync.md deleted. This RESPONSE.md is new and was written because the task asked for it. Tests: python -B -m unittest discover -s tests -t . reports 4 tests, OK.
