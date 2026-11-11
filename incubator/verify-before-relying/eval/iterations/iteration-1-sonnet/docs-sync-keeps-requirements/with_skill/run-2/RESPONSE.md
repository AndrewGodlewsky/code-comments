I updated two stale descriptions in `docs/limits.md`. I changed no code. I did not run the tests.

**Corrected to match the code**
- Search page size: the doc said 50, but `PAGE_SIZE = 100` (`app/config.py:4`), and `tests/test_portal.py:11` pins 100. It now says 100.
- Address lookup timeout: the doc said 5 seconds, but `GEOCODE_TIMEOUT_SECONDS = 10` (`app/config.py:10`). `app/geocode.py:13` passes it to the request. It now says 10.

**Checked and left as written**
- The export runs nightly at 02:00 UTC. `EXPORT_HOUR_UTC = 2` and `next_export` in `app/schedule.py`, plus the two tests in `tests/test_portal.py`, confirm it.
- Address lookups go to the Mapline geocoding API. `app/geocode.py:5` points at it.

**Conflicts where the code breaks a requirement or outside fact (doc text kept, possible bugs)**
1. Mapline rate limit (`docs/limits.md:10`). The doc says Mapline's free tier allows 100 requests a minute per key. The code is configured for `GEOCODE_REQUESTS_PER_MINUTE = 250` (`app/config.py:7`), and `app/geocode.py:8` paces lookups at that rate. If the portal is on the free tier, it will exceed the supplier's limit. Someone should confirm the plan tier or lower the setting.
2. Deleted accounts in the export (`docs/limits.md:16`). The doc says deleted accounts are left out, as section 4 of the privacy policy requires. `export_accounts` in `app/export.py:8-13` does not filter anything. It writes every account passed in, and `deleted` is just an exported column. Unless the caller filters first, which nothing in this repo shows, deleted accounts are exported. This is a possible privacy-policy violation. I could not check the policy itself.
