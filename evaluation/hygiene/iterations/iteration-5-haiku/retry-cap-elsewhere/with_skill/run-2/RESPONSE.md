I changed the report retry limit from three to five.

- `fetcher/config.py`: `MAX_RETRIES` is now `5`. This is the value the fetcher uses.
- `fetcher/client.py`: the module docstring and the wait comment now describe five retries, six attempts in total, and waits of 2, 4, 8, 16 and 32 seconds (62 seconds before `ReportUnavailable` is raised, up from 14).
- `docs/operations.md`: the runbook now says five retries and about 62 seconds.

The unit tests pass (`python -m unittest`). The test checks the cap through `MAX_RETRIES`, so it needed no edit.

Please note that a report that keeps failing now holds the nightly job for about 62 seconds instead of 14. The job still moves on to the next report afterwards.

I did not commit anything. The changes are uncommitted in the working tree.
