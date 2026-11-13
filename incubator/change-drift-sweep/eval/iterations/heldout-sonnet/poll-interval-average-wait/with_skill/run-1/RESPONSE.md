The order poller now checks every ten minutes: `POLL_INTERVAL_S` in `orders/settings.py` is 600 (was 300). The tests pass.

Corrected, by file:
- `orders/poller.py`: the module docstring said "every five minutes"; it now says "every ten minutes".
- `orders/queue.py`: the docstring said an order has waited "about 150 s" on average when queued; it now says "about 300 s" (half of the 600 s interval).
- `docs/operations.md`: "every 5 min" is now "every 10 min", and "at most five minutes" is now "at most ten minutes".
- `docs/fulfilment.md`: the average delay "two and a half minutes" is now "five minutes". The "half a poll interval" explanation was already correct.

Kept as written:
- `docs/operations.md`, 2 October 2026 incident: "ran every 5 minutes" and "5 minutes apart" are a dated record of what happened then.
- `docs/operations.md`, "caches order lists for 5 minutes" is a storefront fact. Polling every 10 minutes now stays above the cache window, so it still holds.
- `docs/operations.md`, "10,000 calls a day" is a storefront quota. At 144 polls a day we are far below it.
- `docs/fulfilment.md`, "five minutes to confirm a picked order" is an unrelated packer rule.
- `docs/operations.md`, "at most 100 orders" is unrelated.

Drift not caused by this change: none found. No instruction files were touched.
