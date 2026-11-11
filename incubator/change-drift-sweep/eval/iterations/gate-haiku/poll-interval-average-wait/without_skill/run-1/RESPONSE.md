The order poller now checks the storefront every ten minutes, not every five.

Changes:
- `orders/settings.py`: `POLL_INTERVAL_S` changed from 300 to 600. This is the only value the poller reads, so the change takes effect everywhere.
- `orders/poller.py`: module docstring updated to "every ten minutes".
- `docs/operations.md`: poll interval now 10 min, and the worst-case delay before an order reaches the fulfilment queue is now ten minutes.
- `README.md`: average pickup delay updated from two and a half minutes to five minutes (half the poll interval).

Checks:
- The storefront caches order lists for 5 minutes, so a 10-minute poll always sees a fresh list. It also cuts poll volume to about 144 calls a day, well under the 10,000 daily limit.
- The duplicate-order fix (each order id queued once) is unchanged, so the 2 October incident cannot recur from this change.
- The historical incident note in `docs/operations.md` still says 5 minutes, because it describes what the poller did at the time.
- `python -m unittest` passes (2 tests). The tests read `POLL_INTERVAL_S`, so they follow the new value.

Trade-off: orders now reach fulfilment up to five minutes later on average and up to ten minutes later at worst. If the fulfilment team relies on the five-minute worst case, they should be told.
