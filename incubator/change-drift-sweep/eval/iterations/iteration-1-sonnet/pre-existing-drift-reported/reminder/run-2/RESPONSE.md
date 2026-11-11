Raised `BATCH_SIZE` from 100 to 250 in `notify/config.py`. That is under the provider's 500-per-call limit. I did not run the tests. They use `BATCH_SIZE` and don't hard-code 100.

Text that stated the old value or a figure computed from it, now corrected:
- `notify/batcher.py` docstring: "batches of up to 100" is now 250.
- `notify/sender.py` docstring: the per-app ceiling was 20 calls/s x 100 = 2,000 notifications/s. It is now 20 x 250 = 5,000.
- `docs/notifications.md`: "up to 100 notifications" is now 250.
- `docs/billing.md`: a burst of 1,000 notifications cost 10 calls. It now costs 4.
- `README.md`: "a hundred at a time" is now "250 at a time".

Left unchanged: the provider's 500-notifications-per-call and 20-calls-per-second limits in `docs/notifications.md`. They are outside facts.

Existing mismatch my change did not cause: `FLUSH_INTERVAL_S` in `notify/config.py` is 30 seconds. `docs/notifications.md` says a partial batch is flushed after 60 seconds and is never held longer than a minute. I did not touch it. Either the doc should say 30 seconds or the config value is wrong, and you should decide which.
