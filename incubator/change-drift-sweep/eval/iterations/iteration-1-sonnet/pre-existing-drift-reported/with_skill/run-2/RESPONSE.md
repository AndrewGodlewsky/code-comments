I raised `BATCH_SIZE` from 100 to 250 in `notify/config.py`. 250 is under the provider's limit of 500 notifications per call, so the change does not break it. I did not run the tests.

I swept every comment, docstring and doc for the old value. That meant the digits 100, the word "hundred", and the figures derived from 100.

**Corrected, by file**
- `notify/batcher.py`: the module docstring now says batches of up to 250.
- `notify/sender.py`: the docstring said one app can push at most 2,000 notifications a second (20 calls × 100). It now says 5,000 (20 × 250).
- `docs/notifications.md`: "up to 100 notifications" is now "up to 250".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls instead of 10 (1000 / 250 = 4).
- `README.md`: "a hundred at a time" is now "250 at a time".

**Kept as written**
- `docs/notifications.md` still says the provider accepts at most 500 notifications per call and 20 calls a second per app. Those are the provider's limits, not ours, and the new size stays inside them.
- `tests/test_batcher.py` uses the `BATCH_SIZE` constant instead of a number, so it needs no change.
- There are no changelog entries, ADRs or instruction-file lines that state the old value.

**Drift that was already there (not caused by this change)**
- `docs/notifications.md` says a partial batch is flushed after 60 seconds, "never held longer than a minute". The code has `FLUSH_INTERVAL_S = 30` in `notify/config.py`. The code is what runs, so the doc is wrong by a factor of two.
- I left it alone because it is unrelated to your request. If you want it fixed, I would change the doc to 30 seconds and the "minute" wording, not the code.
