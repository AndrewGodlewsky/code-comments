The fetcher now retries five times instead of three before raising `ReportUnavailable`.

Changes:
- `fetcher/config.py`: `MAX_RETRIES` is now 5.
- `fetcher/client.py`: the module docstring now says five retries and at most six attempts. The wait comment now reads 2, 4, 8, 16 and 32 seconds, 62 seconds in all (it was 14).
- `docs/operations.md`: the retry count is now five, and the give-up time is about 62 seconds (it was 14).

The unit tests pass (2 tests). The retry-cap test reads `MAX_RETRIES`, so it follows the change without edits.

Two things need your input:
- No reason was given for the change, so the code records only the new value. If there is a reason, such as a reports-team SLA or a known slow-service window, tell me and I will add it beside `MAX_RETRIES`.
- The total wait goes from about 14 seconds to about 62 seconds. The nightly job will spend longer on each failing report. Confirm that is acceptable to the reports team.
