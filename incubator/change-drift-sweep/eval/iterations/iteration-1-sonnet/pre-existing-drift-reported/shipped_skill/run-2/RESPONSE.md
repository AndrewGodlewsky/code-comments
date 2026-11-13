I raised `BATCH_SIZE` from 100 to 250 in `notify/config.py`.

The change also made some statements about the old size false, so I updated them:
- `notify/batcher.py`: the module docstring now says batches of up to 250.
- `notify/sender.py`: the docstring said one app can push at most 2,000 notifications a second (20 calls x 100). It now says 5,000 (20 calls x 250).
- `docs/notifications.md` and `README.md`: both now say 250 per call.
- `docs/billing.md`: the example said a burst of 1,000 notifications costs 10 calls. It now says 4.

250 is within the provider's limit of 500 notifications per call, so I left that line as written.

I found one existing problem that my change did not cause, and I left it alone. `docs/notifications.md` says a partial batch is flushed after 60 seconds and is never held longer than a minute. `FLUSH_INTERVAL_S` in `notify/config.py` is 30. I don't know which value is intended. Tell me which one is right and I'll correct the other.

You gave the per-call cost as the reason for the change, which `docs/billing.md` already covers, so I added no new rationale comment.
