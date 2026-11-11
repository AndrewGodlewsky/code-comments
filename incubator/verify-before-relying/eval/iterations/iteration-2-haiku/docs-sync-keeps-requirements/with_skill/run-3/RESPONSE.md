I updated docs/limits.md to match the code. No code was changed.

Corrected (descriptions, checked against the code and config):

- Search section: the doc said 50 results per page. `PAGE_SIZE = 100` in app/config.py, and app/search.py `page()` slices by it. Changed to 100.
- Address lookups section: the doc said a lookup gives up after 5 seconds. `GEOCODE_TIMEOUT_SECONDS = 10` in app/config.py, passed as the request timeout in app/geocode.py. Changed to 10 seconds.
- Account export section: "runs nightly at 02:00 UTC" matches `EXPORT_HOUR_UTC = 2` and app/schedule.py `next_export()`. Checked out, left as is.

Kept as written, and reported as conflicts with the code:

1. Account export, "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." This mixes a description with a requirement (it cites a policy), so I kept the whole sentence. The code does not do it: app/export.py `export_accounts()` writes every account it is given, and `deleted` is one of the exported FIELDS. Nothing in app/ filters deleted accounts. This is a possible bug against the privacy policy requirement. Not fixed, since you asked for no code changes.
2. Address lookups, "Mapline's free tier allows 100 requests a minute per API key." This is an outside fact about Mapline, so I kept it. It conflicts with the code: app/config.py sets `GEOCODE_REQUESTS_PER_MINUTE = 250`, which is the rate the portal sends to Mapline, and app/geocode.py paces calls to that rate. If the portal is on the free tier, it will exceed Mapline's 100 requests per minute. Possible bug, reported only.

No tests were run and no probes were needed; the claims were settled by reading the config and the code that uses it.
