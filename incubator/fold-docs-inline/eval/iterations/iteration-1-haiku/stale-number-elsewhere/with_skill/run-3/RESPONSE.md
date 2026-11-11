I folded docs/order-sync.md into the code and deleted the page, since no claim on it still needs a document. Only orders/client.py changed.

Fate list, in page order:

1. "`orders/sync.py` makes the nightly copy of shop orders into the warehouse store." Dropped. The module docstring of orders/sync.py already says this.
2. "`sync_orders()` reads the shop API one page at a time; an empty page means there are no more orders to read." Dropped. orders/sync.py loops over pages and returns on an empty page, and the get_page docstring in orders/client.py says it returns an empty list once every order has been read.
3. "`ShopClient.get_page()` tries each request up to 5 times" Dropped. ATTEMPTS = 5 in orders/settings.py, used by the loop in ShopClient.get_page.
4. "2 seconds apart" Not migrated. orders/backoff.py pause_after(n) returns PAUSE_SECONDS * 2 ** (n - 1), so the waits between the 5 attempts are 2, 4, 8 and 16 seconds, not a flat 2 seconds. orders/settings.py describes PAUSE_SECONDS as the wait after the first failed attempt, and tests/test_client.py only checks one pause after one failure, which fits both readings. No comment was written for this claim.
5. "because the shop API drops about one request in a thousand during its nightly maintenance (OPS-19)." Moved to orders/client.py, as a comment above the retry loop in ShopClient.get_page, with the ticket id kept.
6. "`PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with HTTP 400 and returns no orders." Moved to orders/client.py, as a comment above PAGE_SIZE. The comment does not state the value 200, which comes from the code.
7. "`OrderStore.upsert()` replaces any stored order that has the same order id." Dropped. orders/store.py upsert sets rows[order["id"]], and the class docstring says orders are keyed by the shop's order id.

Question for you: which pause is right, the flat 2 seconds on the page or the doubling backoff in the code? I left the code as it is. The page is deleted, so if you want the flat-2-seconds version kept, the page's text needs restoring from history and the code or the page needs to change.

Other files that state a moved fact: none. No file links to docs/order-sync.md. docs/deployment.md and README.md do not mention it.

Gaps for you to check:
- The "one request in a thousand" rate (OPS-19) cannot be checked against this repository. It is now in the comment in orders/client.py as the page stated it.
- Nothing in the tests checks the PAGE_SIZE limit of 250, so the comment is the only record of it.
- docs/deployment.md is unchanged and is outside the scope of this page.
