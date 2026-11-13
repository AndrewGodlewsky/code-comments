The notification batch size is now 250 (`notify/config.py`, `BATCH_SIZE = 250`). The provider accepts up to 500 notifications per call, so 250 is within its limit.

Prose I corrected to match:
- `notify/batcher.py` module docstring: "batches of up to 100" now reads "up to 250".
- `notify/sender.py` docstring: the per-app ceiling was derived from the old batch size (20 calls a second × 100 = 2,000). It is now 20 × 250 = 5,000 notifications a second.
- `README.md`: "a hundred at a time" now reads "two hundred and fifty at a time".
- `docs/notifications.md`: "up to 100 notifications" now reads "up to 250".
- `docs/billing.md`: a burst of 1,000 notifications is now 1,000 / 250 = 4 calls, not 10. Partial batches still cost one extra call each.

Kept as written:
- `docs/notifications.md`, "at most 500 notifications per call and 20 calls a second per app": a provider limit (outside fact). 250 still fits under it.
- `docs/billing.md`, "Invoices arrive on the first working day of each month": unrelated to the batch size.

Drift this change did not cause:
- `docs/notifications.md` says a partial batch is flushed after 60 seconds, and "a minute" in the same sentence. The code sets `FLUSH_INTERVAL_S = 30` in `notify/config.py`. This was already false before my change. I did not correct it, since the request was only about batch size. The fix would be to change the doc's 60 seconds and "a minute" to 30 seconds and half a minute, toward the code.

Tests: `python -m unittest` in the repository passes.
