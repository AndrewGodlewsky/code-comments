The order poller now checks for new orders every ten minutes. `POLL_INTERVAL_S` in `orders/settings.py` went from 300 to 600. I did not run the tests.

I searched the code comments, docstrings and Markdown docs for the old value and for figures derived from it, and corrected these:
- `orders/poller.py`: the module docstring now says every ten minutes.
- `docs/operations.md`: "every 5 min" is now "every 10 min", and the worst-case delay is now "at most ten minutes".
- `docs/fulfilment.md`: the average wait is now five minutes. It was two and a half minutes, half the old interval, and half of 10 minutes is 5.
- `orders/queue.py`: the "about 150 s" average wait is now "about 300 s" (600 / 2). That figure never contained the old interval, so a search for "5 minutes" would have missed it.

I left these unchanged:
- The "5 minutes" cache fact in `docs/operations.md` is the storefront's own cache lifetime, not our interval. Polling every 10 minutes is slower than that cache, so it does not conflict with it.
- The 2 October 2026 incident entry in `docs/operations.md` is a dated record, so it keeps "ran every 5 minutes" and "5 minutes apart".
- The packer's five-minute confirmation window in `docs/fulfilment.md` is a different limit that happens to share the number.
- The 10,000 calls a day figure is the storefront's limit and still holds. Polling every ten minutes is about 144 calls a day.

I found no drift that predates this change and no instruction-file lines to flag.
