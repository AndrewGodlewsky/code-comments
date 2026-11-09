The retry cap for report fetches is now five retries instead of three, so a report is attempted up to six times before ReportUnavailable is raised.

Changes:
- fetcher/config.py: MAX_RETRIES changed from 3 to 5. The retry loop and the test read this constant, so no other code change was needed.
- fetcher/client.py: the module docstring now says five retries and six attempts, and the wait comment now gives the new waits (2, 4, 8, 16 and 32 seconds, 62 seconds in all). The old comment said 14 seconds, which would have been false.
- docs/operations.md: the operations note now says five retries and about 62 seconds before a report is given up on. I updated it because it describes this behaviour and would otherwise be wrong for the nightly job.

Checks: the unit tests in tests/test_client.py pass (2 tests). The retry-cap test uses MAX_RETRIES, so it now expects six calls.

Please note: the nightly job will now wait about 62 seconds per timing-out report instead of about 14 seconds. If that matters for the job's schedule, the reports team may want to confirm it.
