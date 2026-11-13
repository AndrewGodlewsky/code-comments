I folded docs/stock-feed.md into the code and deleted the page. One claim needs your decision.

Fate list, in page order:

1. "`stock_rows()` leaves out SKUs that have no stock." - Dropped. stock/rows.py:5 filters `qty > 0`, and tests/test_feed.py `test_rows_skip_empty_stock` checks it.
2. "`stock_rows()` must return rows sorted by SKU" - Not migrated. stock/rows.py:5 does return `sorted(...)`, and the test expects sorted output, so the sort is real. But the page's only reason is contradicted by stock/feed.py:14, where `write_feed` calls `sorted(rows)` itself, so nothing in this repo needs `stock_rows()` output to be sorted. Quoted here, not placed in a comment. Which side is right: keep the sort as a rule with a different reason, or drop the rule?
3. "`write_feed()` walks the rows and the price list together in a single merge pass" - Dropped. stock/feed.py:9-10 docstring already says so.
4. "a row that arrives out of order is silently skipped" - Not migrated. stock/feed.py:12 and :14 sort both prices and rows before the merge, so out-of-order input is not skipped. `test_feed_skips_unpriced` covers only unpriced SKUs.
5. "Each feed line is tab-separated: SKU, quantity and price." - Dropped. stock/format.py:7 docstring and the `\t` f-string at :8 state it.
6. "Quantities are capped at `MAX_FEED_QTY` (9999)" - Dropped. stock/format.py:3 sets 9999, :8 applies `min()`, and `test_line_caps_quantity` checks it.
7. "because the marketplace's feed format has a four-digit quantity column and rejects the whole file if any value is longer (MKT-204)" - Moved to stock/format.py, as a comment above `MAX_FEED_QTY`, the symbol whose change would break it. The ticket id is kept. The four-digit width agrees with the value 9999.

Edits:
- stock/format.py: two-line comment added above `MAX_FEED_QTY`. No code changed.
- docs/stock-feed.md: deleted. Every claim on it is dropped, moved, or not migrated, so no kept claim remained and you asked for the page to go.
- Tests: `python -I -m unittest discover -s tests -t .` runs 3 tests, all OK.

Other files: no other file states the moved fact. docs/marketplace.md does not mention the quantity limit or MKT-204, and README.md does not either. No file links to docs/stock-feed.md.

Gaps:
- The four-digit column and whole-file rejection come from the page. Nothing in this repo verifies them, and MKT-204 is not in the repo.
- Because the page is deleted, the wording of claims 2 and 4 survives only in this file.
- Claim 2 needs your decision before any sort comment is written.
