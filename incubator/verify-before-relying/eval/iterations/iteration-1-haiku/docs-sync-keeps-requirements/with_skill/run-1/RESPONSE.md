I updated docs/limits.md to match the code. No code was changed.

False descriptions I corrected:

- docs/limits.md:5 said "Search returns 50 results per page." app/config.py:4 sets PAGE_SIZE = 100, app/search.py:8-9 slices by PAGE_SIZE, and tests/test_portal.py:13-14 pins 100 per page. Changed to 100.
- docs/limits.md:11 said "A lookup gives up after 5 seconds." app/config.py:10 sets GEOCODE_TIMEOUT_SECONDS = 10, and app/geocode.py:13 passes it as the request timeout. Changed to 10 seconds.

Checked and trusted, left as written:

- docs/limits.md:9 (lookups go to the Mapline geocoding API): matches the URL in app/geocode.py:5.
- docs/limits.md:15 (export runs nightly at 02:00 UTC): matches EXPORT_HOUR_UTC = 2 in app/config.py:13 and app/schedule.py, and tests/test_portal.py:25-31 pins 02:00 UTC.

Requirements and outside facts the code breaks (kept as written, reported only):

1. docs/limits.md:10, "Mapline's free tier allows 100 requests a minute per API key." This is an outside fact about Mapline. The code breaks it: app/config.py:7 sets GEOCODE_REQUESTS_PER_MINUTE = 250, and the portal is configured to send up to 250 lookups a minute. Either the configured rate or the free-tier assumption needs review. I did not change either.

2. docs/limits.md:16, "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." This mixes a description with a requirement that cites a policy, so I kept the whole sentence. The description part is false: app/export.py:8-13 writes every account it is given, including rows where deleted is True (FIELDS includes "deleted", and there is no filter). No caller in the repository filters deleted accounts before export. So the code does not meet the privacy-policy requirement as far as this repository shows. This is a possible bug to review, not a doc fix. I did not change the code.

Observation, not a doc claim: app/geocode.py:8 defines MIN_INTERVAL, which is the spacing that would keep the portal at its configured rate, but lookup() never uses it. This is consistent with the 250/min conflict above.

Files changed: docs/limits.md. Added: RESPONSE.md.
