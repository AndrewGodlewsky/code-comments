# Order sync

`orders/sync.py` makes the nightly copy of shop orders into the warehouse store.

- `sync_orders()` reads the shop API one page at a time; an empty page means there are no
  more orders to read.
- `ShopClient.get_page()` tries each request up to 5 times, 2 seconds apart, because the
  shop API drops about one request in a thousand during its nightly maintenance (OPS-19).
- `PAGE_SIZE` has to stay at 250 or below: the shop API answers a larger page size with
  HTTP 400 and returns no orders.
- `OrderStore.upsert()` replaces any stored order that has the same order id.
