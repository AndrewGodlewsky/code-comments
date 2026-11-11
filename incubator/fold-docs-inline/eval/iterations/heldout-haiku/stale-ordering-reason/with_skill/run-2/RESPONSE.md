# docs/stock-feed.md retired

I moved the one fact that belongs in code into a comment, dropped the claims the code already states, and deleted `docs/stock-feed.md` because no claim needed to stay a document. One claim contradicts the code and I did not migrate it; you need to decide that one.

## Fate list

| # | Claim (page order) | Fate | Evidence |
|---|---|---|---|
| 1 | "`stock_rows()` leaves out SKUs that have no stock." | Dropped | `stock/rows.py:6` filters `qty > 0`; `tests/test_feed.py:10-11` |
| 2 | "`stock_rows()` must return rows sorted by SKU" | Dropped | `stock/rows.py:6` calls `sorted(...)`. Nothing relies on this order, because `write_feed()` sorts its own input (`stock/feed.py:12`, `:14`). Dropped rather than moved because the page's only reason is false (see row 3). |
| 3 | "`write_feed()` walks the rows and the price list together in a single merge pass" | Dropped | `stock/feed.py:9-10` docstring already states the merge pass |
| 4 | "a row that arrives out of order is silently skipped" | Not migrated | Contradicted by `stock/feed.py:12` (`sorted(prices)`) and `:14` (`sorted(rows)`): `write_feed()` sorts both inputs itself, so out-of-order rows are not skipped. No comment added, no code changed. |
| 5 | "Each feed line is tab-separated: SKU, quantity and price." | Dropped | `stock/format.py:7` docstring; `stock/format.py:8` f-string |
| 6 | "Quantities are capped at `MAX_FEED_QTY` (9999)" | Dropped | `stock/format.py:3` value; `stock/format.py:8` `min(qty, MAX_FEED_QTY)`; `tests/test_feed.py:13-14` |
| 7 | "because the marketplace's feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204)" | Moved | `stock/format.py:3-4`, a comment above `MAX_FEED_QTY`. Changing the value breaks the feed, so the constant is the narrowest owner. Ticket MKT-204 kept. |

## Edits

- `stock/format.py`: added a two-line comment above `MAX_FEED_QTY` (row 7). No other code changed.
- `docs/stock-feed.md`: deleted. Every claim on it is dropped, moved, or not migrated, so no kept claim remains.
- `docs/` still holds `marketplace.md`. No folder was deleted.

## Other files

- No other file states the moved fact. Searches for `MKT-204`, `four-digit`, `9999` and `MAX_FEED_QTY` found only `stock/format.py` and the test.
- No file links to `docs/stock-feed.md`. `README.md` and `docs/marketplace.md` do not link to it.

## Gaps for you to fill

- **Row 4 needs your decision.** Either `write_feed()` should rely on pre-sorted input, which would be a code change and is out of scope here, or the claim is stale and can stay gone. The original text is only in version history now, since the page is deleted.
- **Row 7 is an outside fact.** The four-digit column and whole-file rejection come from the marketplace (MKT-204). Nothing in this repo verifies them, so the comment repeats the page's claim as written.
