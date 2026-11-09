The report fetcher now retries five times instead of three before raising ReportUnavailable.

Changes:
- fetcher/config.py: MAX_RETRIES is 5. The retry loop in fetcher/client.py reads this constant, so it needed no edit.
- fetcher/client.py: the module docstring now says five retries and at most six attempts, and the wait comment now gives the waits as 2, 4, 8, 16 and 32 seconds, 62 seconds in total.
- docs/operations.md: "three times" is now "five times", and "about 14 seconds" is now "about 62 seconds".

The existing tests use MAX_RETRIES, so they check the new cap automatically. Both pass (`python -m unittest discover -s tests -t .`).

Worth knowing: a report that keeps timing out now holds the nightly job for about 62 seconds per report instead of about 14.
