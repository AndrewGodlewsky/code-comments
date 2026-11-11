I raised `BATCH_SIZE` from 100 to 250 in `notify/config.py`, and updated the prose that restated the old value or figures derived from it.

**Corrected**
- `notify/batcher.py`: module docstring now says "batches of up to 250".
- `notify/sender.py`: docstring's per-app ceiling is now 5,000 notifications a second (20 calls a second x 250; was 2,000).
- `README.md`: "a hundred at a time" is now "250 at a time".
- `docs/notifications.md`: "up to 100 notifications" is now "up to 250".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (1000 / 250; was 10). "Each partial batch costs one more" is unchanged.

**Kept**
- `docs/notifications.md`: the provider accepts at most 500 notifications per call and 20 calls a second. This is the provider's own limit and stays as written. 250 is within it, so the change does not break it. The 20 calls a second is also unchanged.
- No changelog, ADR or instruction files in this repo were touched.

**Drift that predates this change (not corrected)**
- `docs/notifications.md` says a partial batch is flushed after 60 seconds ("never held longer than a minute"), but `FLUSH_INTERVAL_S` in `notify/config.py` is 30 seconds. The code is what runs, so the doc is the stale side. I left it as it is and did not change the code. Say if you want the doc changed to 30 seconds and "half a minute".

The tests use `BATCH_SIZE` rather than a literal, so they needed no edit.
