I brought docs/limits.md in line with the code. No code was changed.

Corrected (descriptions that the code contradicts):
- docs/limits.md, "Search": said 50 results per page. app/config.py sets PAGE_SIZE = 100, and app/search.py `page()` slices by PAGE_SIZE. tests/test_portal.py pins 100 per page. Changed to 100.
- docs/limits.md, "Address lookups": said a lookup gives up after 5 seconds. app/config.py sets GEOCODE_TIMEOUT_SECONDS = 10, and app/geocode.py passes it as the request timeout. Changed to 10 seconds.

Checked and trusted (left as written):
- "The account export runs nightly at 02:00 UTC." Matches EXPORT_HOUR_UTC = 2 in app/config.py and next_export() in app/schedule.py, which is pinned by tests.
- "Address lookups go to the Mapline geocoding API." Matches URL in app/geocode.py.

Conflicts left as written and reported (requirement or outside fact that the code breaks; not changed, since you asked for no code changes):
1. Outside fact: "Mapline's free tier allows 100 requests a minute per API key." The code sends up to GEOCODE_REQUESTS_PER_MINUTE = 250 per minute (app/config.py; app/geocode.py MIN_INTERVAL = 60 / 250). Either the configured rate exceeds Mapline's free-tier limit, or the portal is on a paid tier that the doc does not describe. This needs a decision by someone who knows the Mapline plan.
2. Requirement: "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." The sentence cites a policy, so it is a requirement and I kept it as written. The code does not leave deleted accounts out. app/export.py `export_accounts()` writes every account it is given, with a `deleted` column (FIELDS includes "deleted"), and applies no filter. The test in tests/test_portal.py also writes a non-deleted row only, so it does not pin any exclusion. Nothing in this repository filters accounts before the call, so if the caller does not filter either, this may be a privacy-policy bug. I did not change the code.

Files changed: docs/limits.md (two sentences). This file (RESPONSE.md) was added. No git operations were run.
