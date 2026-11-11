The order poller now checks the storefront every ten minutes instead of every five.

Changes:
- `orders/settings.py`: `POLL_INTERVAL_S` is now 600. The comment records the reason, the storefront team's request to reduce load on their API.
- `orders/poller.py`: the module docstring no longer hard-codes the interval. It points to `POLL_INTERVAL_S`.
- `orders/queue.py`: the average queueing delay is now described as half a poll interval, not a fixed 150 s, which becomes 300 s at the new interval.
- `docs/operations.md`: poll frequency and worst-case delay are now ten minutes. The 2 October 2026 incident record is unchanged because it describes the past.
- `docs/fulfilment.md`: the average delay before an order reaches the packing screen is now five minutes, not two and a half.

Checks:
- The 10-minute interval is still longer than the storefront's 5-minute order-list cache, so each poll gets fresh data.
- Polling less often lowers the storefront call volume, well under its 10,000 calls a day per key.
- The unit tests pass (`python -m unittest`).

Please confirm two things:
- The storefront team's request is the only reason for the change. If there is a more specific reason, such as a rate-limit incident or a contract term, I can record it in `orders/settings.py`.
- Ten minutes is the agreed value. The worst-case delay for a new order is now ten minutes, so the packing team should know about the longer wait.
