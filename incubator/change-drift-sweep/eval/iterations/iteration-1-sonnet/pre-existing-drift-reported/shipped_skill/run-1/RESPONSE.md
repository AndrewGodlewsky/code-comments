Raised the notification batch size from 100 to 250 (`BATCH_SIZE` in `notify/config.py`). Tests pass.

Statements of the old behaviour that I updated so none still say 100:
- `notify/batcher.py` module docstring: batches of up to 250.
- `notify/sender.py` docstring: one app's ceiling is now 20 calls/s x 250 = 5,000 notifications a second (was 2,000). The 20 calls a second provider limit is unchanged.
- `docs/notifications.md` and `README.md`: 250 per call.
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (was 10).

The provider's limit of 500 notifications per call is an outside fact, so I left it as written; 250 is within it.

Existing mismatch I did not touch: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. This predates this change and is unrelated to batch size. Please say which is intended (30s or 60s) and I will correct the other.

No reason was given for the move to 250 beyond cost per call, and I did not record one in a comment.
