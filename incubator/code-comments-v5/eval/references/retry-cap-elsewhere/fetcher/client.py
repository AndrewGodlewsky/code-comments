"""Client for the reports service.

fetch_report() gives up after five retries, so a caller sees at most six
attempts before ReportUnavailable is raised.
"""

import time

from fetcher.config import BACKOFF_SECONDS, MAX_RETRIES


class ReportUnavailable(Exception):
    """The reports service did not answer in time."""


def fetch_report(session, report_id, sleep=time.sleep):
    """Return the report body, retrying on timeouts.

    Raises ReportUnavailable when every attempt times out.
    """
    wait = BACKOFF_SECONDS
    for attempt in range(MAX_RETRIES + 1):
        try:
            return session.get(f"/reports/{report_id}")
        except TimeoutError:
            if attempt == MAX_RETRIES:
                break
            # Waits are 2, 4, 8, 16 and 32 seconds: 62 seconds in all before we give up.
            sleep(wait)
            wait *= 2
    raise ReportUnavailable(report_id)
