I updated docs/limits.md and changed no code. Two statements in it conflict with the code. I left both as written, so you need to decide on them.

**Corrected to match the code**
- Search page size is 100 results, not 50. `PAGE_SIZE` in `app/config.py` is 100, and the paging test checks it.
- An address lookup times out after 10 seconds, not 5. `GEOCODE_TIMEOUT_SECONDS` is 10 and `app/geocode.py` passes it as the request timeout.
- The nightly export at 02:00 UTC was already correct. `EXPORT_HOUR_UTC` is 2, and the schedule tests confirm it.

**Conflicts I kept as written**
1. **Mapline rate limit.** The doc says Mapline's free tier allows 100 requests a minute per API key. That is an outside fact, so I kept it. The code is configured for 250 requests a minute (`GEOCODE_REQUESTS_PER_MINUTE`). `MIN_INTERVAL` in `app/geocode.py` is computed from that value, though `lookup()` never uses it, so nothing enforces the rate. If the portal is on the free tier, 250 a minute is over the limit. Either the setting should drop to 100 or lower, or the plan or tier assumption needs checking.
2. **Deleted accounts in the export.** The doc says deleted accounts are left out, as section 4 of the privacy policy requires. I kept that as a requirement. The code does not do it. `export_accounts` writes every account it is given, and `deleted` is just a column in the CSV. Nothing in `app/export.py` filters them out unless the caller does, and I found no caller or test that does. The export therefore appears to break the stated requirement. The code probably needs a filter, or someone needs to confirm where deleted accounts are removed.

I only had the files in this directory, so I could not check the privacy policy text or the Mapline plan terms.
