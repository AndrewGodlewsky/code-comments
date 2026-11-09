Done: the fetcher now retries five times instead of three.

- `fetcher/config.py`: `MAX_RETRIES` changed from 3 to 5.
- `fetcher/client.py`: updated the docstring (five retries, at most six attempts) and the backoff comment.
- `docs/operations.md`: now says five retries.

Side effect: with doubling waits (2, 4, 8, 16, 32 seconds), a failing report now takes about 62 seconds to give up, up from about 14. I updated the docs and comment to say so. The nightly job will take longer when the service is down. The existing tests pass.
