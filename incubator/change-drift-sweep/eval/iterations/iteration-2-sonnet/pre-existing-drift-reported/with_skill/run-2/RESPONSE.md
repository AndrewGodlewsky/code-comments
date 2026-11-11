Batch size is now 250 (`BATCH_SIZE` in `notify/config.py`). Tests pass. 250 is under the provider's cap of 500 per call.

Corrected, because they stated the old value:
- `notify/batcher.py`: module docstring, "up to 100" is now "up to 250".
- `docs/notifications.md`: "up to 100 notifications" is now "up to 250".
- `README.md`: "a hundred at a time" is now "250 at a time".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (1,000 / 250), not 10. This is a derived figure.
- `notify/sender.py`: docstring maximum of 2,000 notifications a second is now 5,000 (20 calls a second x 250).

Kept as written:
- The provider's "at most 500 notifications per call and 20 calls a second" in `docs/notifications.md` is an outside fact. The new size does not break it.

Drift that was already there, not caused by this change:
- `docs/notifications.md` said a partial batch is flushed after 60 seconds (never held longer than a minute). The code has `FLUSH_INTERVAL_S = 30`. I corrected the doc toward the code: "after 30 seconds ... never held longer than half a minute". I did not change the code. If 60 seconds was the intent, change the constant instead and I will revert the doc.

No instruction files, ADRs or changelog entries were affected.
