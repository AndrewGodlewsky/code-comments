The fetcher now retries five times instead of three before giving up on a report.

Changes:
- `fetcher/config.py`: `MAX_RETRIES` changed from 3 to 5. The existing test uses this constant, so it follows the new value.
- `fetcher/client.py`: updated the module docstring to say five retries and at most six attempts.
- `docs/operations.md`: updated to say five retries. Because the waits double from 2 seconds (2+4+8+16+32), a report that keeps failing now takes about 62 seconds to give up, up from about 14.

I ran the tests and they pass.

Heads up: each failing report now holds the nightly job for about 62 seconds instead of 14, so a bad night with many failing reports will run noticeably longer. If that is a concern, we could cap the wait between retries.
