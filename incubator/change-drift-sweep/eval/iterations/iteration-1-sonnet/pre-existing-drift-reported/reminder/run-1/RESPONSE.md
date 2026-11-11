I raised `BATCH_SIZE` from 100 to 250 in `notify/config.py`. 250 is under the provider's limit of 500 notifications per call, so it is safe. I did not run the tests.

Statements of the old size or figures computed from it that I updated:
- `notify/batcher.py` module docstring: "batches of up to 250".
- `notify/sender.py` docstring: one app can now push at most 5,000 notifications a second (20 calls a second x 250), up from 2,000.
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls, down from 10.
- `docs/notifications.md`: "up to 250 notifications in one provider call".
- `README.md`: "a hundred at a time" is now "250 at a time".

I left the provider limits of 500 per call and 20 calls a second alone, because they are facts about the provider.

One mismatch my change did not cause, which I did not fix: `docs/notifications.md` says a partial batch is flushed after 60 seconds ("never held longer than a minute"), but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. The doc is probably stale. Tell me which is intended and I will change it.
