I updated two lines in docs/limits.md to match the code and changed no code.

Corrected (descriptions that had drifted):
- Search: "50 results per page" is now "100". `PAGE_SIZE` in app/config.py is 100, and `test_pages_hold_page_size_results` in tests/test_portal.py pins that.
- Address lookups: "gives up after 5 seconds" is now "10 seconds". `GEOCODE_TIMEOUT_SECONDS` is 10 and `lookup` in app/geocode.py passes it as the timeout.

Checked and left as written: "The account export runs nightly at 02:00 UTC." `EXPORT_HOUR_UTC` is 2, `next_export` in app/schedule.py uses it, and the schedule tests pin it.

Kept as written, but the code breaks them. These are possible bugs. I did not change the doc or the code:
- Address lookups, Mapline's free tier: the doc says it allows 100 requests a minute per API key. This is an outside fact about the supplier. `GEOCODE_REQUESTS_PER_MINUTE` in app/config.py is 250, and `MIN_INTERVAL` in app/geocode.py paces lookups at that rate. At that rate the portal would exceed the free-tier limit. Either the config value is too high or the account is not on the free tier. Someone should check which.
- Account export, deleted accounts: the doc says they are left out, as section 4 of the privacy policy requires. This is a requirement. `export_accounts` in app/export.py does not filter. It writes every account, and `deleted` is just a column in the CSV. So deleted accounts are exported today, which may be a privacy-policy violation. The code needs a fix, and I left that to you because you asked for no code changes.
