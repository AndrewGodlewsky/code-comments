# Operating the report fetcher

When the reports service times out, the fetcher retries five times with doubling
waits, starting at two seconds. A report that still fails after about 62 seconds
raises `ReportUnavailable`, and the nightly job moves on to the next report.

Check the service status page before re-running a failed night.
