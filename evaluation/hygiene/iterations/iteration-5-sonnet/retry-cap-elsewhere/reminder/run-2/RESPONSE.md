The fetcher now retries five times instead of three before giving up on a report.

- `fetcher/config.py`: `MAX_RETRIES` changed from 3 to 5. This is the only functional change. The existing test uses the constant, so it needed no edit.
- Comments and docs that the change made false:
  - `fetcher/client.py`: the module docstring now says "five retries" and "at most six attempts". The backoff comment now reads "2, 4, 8, 16 and 32 seconds: 62 seconds in all".
  - `docs/operations.md`: now says "five times" and "about 62 seconds".

The total wait before `ReportUnavailable` goes from 14 to 62 seconds per failing report, because the waits keep doubling. That may matter for the nightly job's overall run time. If the reports team wants a shorter worst case, the backoff would need a cap. I haven't changed that.
