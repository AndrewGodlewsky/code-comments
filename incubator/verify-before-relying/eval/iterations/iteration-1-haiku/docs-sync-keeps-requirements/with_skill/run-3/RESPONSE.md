I updated docs/limits.md to match the code. No code was changed.

Corrected descriptions:
- docs/limits.md:5 said search returns 50 results per page. app/config.py:4 sets PAGE_SIZE = 100, and app/search.py:8-9 and tests/test_portal.py:12-14 pin 100. Changed to 100.
- docs/limits.md:11 said a lookup gives up after 5 seconds. app/config.py:10 sets GEOCODE_TIMEOUT_SECONDS = 10, passed as the timeout in app/geocode.py:13. Changed to 10. Note that this is the HTTP client's timeout, which applies per connect and read, not as a total cap on the lookup.
- The nightly export at 02:00 UTC (docs/limits.md:15) checks out: app/config.py:13 sets EXPORT_HOUR_UTC = 2 and tests/test_portal.py:25-27 pins it. Left as written.

Requirements and outside facts the code breaks or may break (kept as written, not changed):
- docs/limits.md:16, "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." This is a requirement. app/export.py:8-13 writes every account it is given, with a `deleted` column, and does no filtering. The only filter could be in a caller, and none exists in this repo. This looks like a possible bug: deleted accounts may be exported. Not fixed, since the task was to change docs only.
- docs/limits.md:10, "Mapline's free tier allows 100 requests a minute per API key." This is an outside fact. app/config.py:6-7 sets GEOCODE_REQUESTS_PER_MINUTE = 250, which exceeds 100 if the portal runs on the free tier. Whether it does is not visible in the repo.

Other observations (not edited):
- app/geocode.py:7-8 defines MIN_INTERVAL from the 250/min setting, but nothing uses it, and lookup() does not pace calls. The portal therefore does not enforce any rate limit in this code, so the docs should not describe one.
- app/schedule.py only computes the next export start. No code in this repo runs the nightly export, so "runs nightly" is based on the schedule calculation, not a scheduler.
