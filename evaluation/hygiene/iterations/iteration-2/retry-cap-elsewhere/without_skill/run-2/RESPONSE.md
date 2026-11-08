The fetcher now retries five times instead of three before giving up on a report.

What changed:
- `fetcher/config.py`: `MAX_RETRIES` goes from 3 to 5. A report now gets six attempts in total (one first try plus five retries), up from four.
- `fetcher/client.py`: the module docstring and the backoff comment were updated to match. The waits are now 2, 4, 8, 16 and 32 seconds, so a report that keeps timing out gives up after about 62 seconds instead of 14.
- `docs/operations.md`: the retry count and the give-up time were updated the same way.

The retry loop itself did not need code changes; it reads `MAX_RETRIES`. The existing unit tests pass (2 of 2), and the test checks against the config constant, so it now expects six attempts.

Worth knowing before this goes out: the nightly job will wait longer on each failing report (about 62 seconds per report versus 14). If the nightly run has a total time budget, that is the number to check.
