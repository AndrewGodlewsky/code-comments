Done. The notification batch size is now 250 (`BATCH_SIZE` in `notify/config.py`). The provider accepts up to 500 notifications per call, so 250 is within its limit. The unit tests pass (`python -m unittest`, 3 tests).

Docs and comments that stated the old value, now corrected:
- `README.md`: "a hundred at a time" is now "two hundred and fifty at a time".
- `docs/notifications.md`: "up to 100 notifications" is now "up to 250".
- `notify/batcher.py` (module docstring): "batches of up to 100" is now "up to 250".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls, not 10 (1,000 / 250 = 4, with no partial batch). Partial-batch wording unchanged.
- `notify/sender.py` (module docstring): at 20 calls a second per app and 250 per call, one app can push at most 5,000 notifications a second, not 2,000.

Left unchanged:
- `docs/notifications.md`: "The push provider accepts at most 500 notifications per call and 20 calls a second per app" is an outside fact from the provider, so it stays.

Drift that was already there before this change (not caused by it, not corrected):
- `docs/notifications.md` says a partial batch is flushed after 60 seconds, and "never held longer than a minute". The code sets `FLUSH_INTERVAL_S = 30` in `notify/config.py`, so the doc is wrong by a factor of two. I left it for you to decide whether the doc or the code should change.
