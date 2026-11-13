I updated docs/limits.md to match the code and changed no code. I checked each statement against app/config.py, the modules that use it, and tests/test_portal.py.

**Corrected to match the code**
- Search page size: 50 became 100 (`PAGE_SIZE`; the paging test also expects 100).
- Lookup timeout: 5 seconds became 10 seconds (`GEOCODE_TIMEOUT_SECONDS`).
- Lookup rate: the doc now says the portal is configured to send up to 250 lookups a minute (`GEOCODE_REQUESTS_PER_MINUTE`). The doc previously gave only Mapline's limit.
- The 02:00 UTC export time was already correct, and the schedule tests confirm it.

**Conflicts I left as written (the doc keeps the requirement; the code disagrees)**
1. **Deleted accounts in the export.** The doc says deleted accounts are left out, as section 4 of the privacy policy requires. `export_accounts` in app/export.py does not filter anything. It writes every account, with `deleted` as a column, and the test passes a row with `deleted` set to False. I kept the sentence because it is a policy requirement. The code appears not to meet it, and you should confirm and fix the code.
2. **Mapline rate limit.** The doc says the free tier allows 100 requests a minute per key. The portal is configured for 250 a minute, so it exceeds that limit if the key is on the free tier. I kept Mapline's figure as an outside fact. Either the plan is above the free tier or the config value needs lowering. Also, `MIN_INTERVAL` in app/geocode.py is computed but nothing calls it, so no throttling is enforced in this code.
