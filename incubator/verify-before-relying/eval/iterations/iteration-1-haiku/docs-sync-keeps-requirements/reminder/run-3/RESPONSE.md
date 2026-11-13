I updated docs/limits.md to match the code. I changed no code and did not run the tests.

What I corrected, after checking against app/config.py, app/search.py, app/geocode.py, app/export.py and tests/test_portal.py:

- Search: the doc said 50 results per page. PAGE_SIZE is 100, and the search test confirms it.
- Address lookups timeout: the doc said 5 seconds. GEOCODE_TIMEOUT_SECONDS is 10.
- Address lookups rate: the doc did not state the portal's rate. I added that it is configured for 250 lookups a minute.
- Account export: the doc said deleted accounts are left out. export_accounts writes every account and includes a `deleted` column. Nothing filters deleted accounts out.

Conflicts for you to decide on (I kept the stated requirement and outside fact as written):

1. Privacy policy: the doc says deleted accounts are left out of the export, as section 4 of the privacy policy requires. The code does not do this, so the export may currently include deleted accounts' data. I left the requirement sentence in place and added a line stating the current behaviour. This is probably the most important item.
2. Mapline rate: the doc says Mapline's free tier allows 100 requests a minute per API key. The portal is configured for 250 a minute, which is above that. Either the config or the free-tier assumption is wrong, or the portal is on a paid tier. I kept the free-tier line as written.
3. Rate limiting is not enforced: GEOCODE_REQUESTS_PER_MINUTE and MIN_INTERVAL exist, but lookup() never waits. The doc now says so. Enforcing it is a code change, which you asked me not to make.
