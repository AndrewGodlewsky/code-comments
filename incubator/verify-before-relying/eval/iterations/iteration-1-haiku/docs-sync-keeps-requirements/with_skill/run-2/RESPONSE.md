I brought docs/limits.md in line with the code. No code was changed.

Descriptions corrected (the code wins):

- docs/limits.md:5 said "Search returns 50 results per page." app/config.py:4 sets PAGE_SIZE = 100, and app/search.py:8-9 and tests/test_portal.py:13 confirm 100. Changed to 100.
- docs/limits.md:11 said "A lookup gives up after 5 seconds." app/config.py:10 sets GEOCODE_TIMEOUT_SECONDS = 10, which app/geocode.py:13 passes as the request timeout. Changed to 10 seconds.
- Added "The portal sends up to 250 lookups a minute." after the Mapline sentence, from app/config.py:7 (GEOCODE_REQUESTS_PER_MINUTE = 250). The doc did not state the portal's own rate before.

Checked and trusted (left as written):

- "The account export runs nightly at 02:00 UTC." matches EXPORT_HOUR_UTC = 2 (app/config.py:13) and app/schedule.py:10-11, and tests/test_portal.py:25-31 pin 02:00 UTC.

Requirements and outside facts the code breaks (kept as written, not changed, reported as possible bugs):

1. Outside fact, docs/limits.md:10: "Mapline's free tier allows 100 requests a minute per API key." The portal is configured to send 250 lookups a minute (app/config.py:7, used by app/geocode.py:8). That exceeds the stated free-tier limit, so lookups past 100 a minute could be rejected or throttled. Either the configured rate or the free-tier assumption needs review. I did not change either.
2. Requirement, docs/limits.md:16: "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." The code does not leave them out. app/export.py:8-13 writes every account it is given and includes a deleted column. I ran export_accounts on an account with deleted=True and it wrote the row "1,x@e.com,pro,True". No filter exists in app/export.py or app/schedule.py. The sentence cites a policy, so I treated it as a requirement and kept it. The export may be exposing deleted accounts to the analytics warehouse, which should be checked.

Verification: the unit tests pass (4 tests, run with python -B so no bytecode was written), and the probes above were run the same way.
