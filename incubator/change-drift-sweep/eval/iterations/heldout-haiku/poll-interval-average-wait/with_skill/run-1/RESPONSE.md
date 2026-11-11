The order poller now checks the storefront every ten minutes instead of every five. The change is `POLL_INTERVAL_S = 600` in `orders/settings.py`. The unit tests pass (`python -m unittest`, 3 tests).

Docs and comments that still described the five-minute interval are updated:

- `orders/poller.py`: module docstring now says "every ten minutes".
- `orders/queue.py`: the average wait before an order is queued is half the poll interval, so it moves from about 150 s to about 300 s.
- `docs/operations.md`: the poll is "every 10 min", and the worst-case delay to the fulfilment queue is "at most ten minutes".
- `docs/fulfilment.md`: the average delay before an order appears on the packing screen is now five minutes, not two and a half.

Kept as written:

- `docs/operations.md`, storefront limits: the storefront caches order lists for 5 minutes. This is an outside fact about the storefront, not our interval. Note that 10-minute polling is now longer than that cache, so each poll sees fresh data.
- `docs/operations.md`, 2 October 2026 incident: a record of what the poller did at the time. Kept.
- `docs/fulfilment.md`, "A packer has five minutes to confirm": a packing deadline, unrelated to the poll interval.

Effect on the storefront quota: the poller now makes 144 calls a day instead of 288, well within the 10,000 calls per key per day limit.
